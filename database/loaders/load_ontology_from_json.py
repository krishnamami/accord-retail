#!/usr/bin/env python3
"""
Accord Retail — Load Knowledge Base JSON into PostgreSQL

Purpose:
  Loads accord_retail_ontology_kb.json into the ontology schema tables.
  
Tables populated:
  - ontology.kb_version
  - ontology.kb_evidence_type (20 types)
  - ontology.kb_decision_type (2 types)
  - ontology.kb_verb (8 verbs)
  - ontology.kb_link
  - ontology.kb_governance_rule
  - ontology.kb_entitlement

Usage:
  python database/loaders/load_ontology_from_json.py
  
  With custom .env path:
  python database/loaders/load_ontology_from_json.py --env /path/to/.env
  
Requirements:
  pip install python-dotenv psycopg2-binary

Environment:
  Reads from .env file:
    DATABASE_HOST
    DATABASE_PORT
    DATABASE_USER
    DATABASE_PASSWORD
    DATABASE_NAME
    KB_JSON_PATH
    KB_VERSION
    KB_ACTIVE
"""

import os
import sys
import json
import argparse
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from uuid import uuid4
from datetime import datetime

# Optional: Use python-dotenv for .env file loading
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

# PostgreSQL connection
try:
    import psycopg2
    from psycopg2.extras import Json
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

# ============================================================================
# SETUP LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE CONNECTION
# ============================================================================

class DBConnection:
    """PostgreSQL connection manager"""
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Connect to PostgreSQL"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                sslmode=os.getenv('DATABASE_SSLMODE', 'require')  # RDS rejects unencrypted connections
            )
            self.cursor = self.conn.cursor()
            logger.info(f"✅ Connected to {self.database}@{self.host}:{self.port}")
        except psycopg2.Error as e:
            logger.error(f"❌ Database connection failed: {e}")
            sys.exit(1)
    
    def execute(self, query: str, params: tuple = None):
        """Execute SQL query"""
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor
        except psycopg2.Error as e:
            logger.error(f"❌ Query failed: {e}")
            logger.error(f"   Query: {query}")
            self.conn.rollback()
            raise
    
    def commit(self):
        """Commit transaction"""
        self.conn.commit()
        logger.info("✅ Transaction committed")
    
    def close(self):
        """Close connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("✅ Database connection closed")

# ============================================================================
# KB LOADER
# ============================================================================

class KBLoader:
    """Load Knowledge Base JSON into PostgreSQL"""
    
    def __init__(self, db: DBConnection, kb_json_path: str, kb_version: str, kb_active: bool = False):
        self.db = db
        self.kb_json_path = kb_json_path
        self.kb_version = kb_version
        self.kb_active = kb_active
        self.kb_data = None
        self.kb_version_id = None
    
    def load_kb_json(self):
        """Load KB JSON file"""
        if not os.path.exists(self.kb_json_path):
            logger.error(f"❌ KB JSON file not found: {self.kb_json_path}")
            sys.exit(1)
        
        try:
            with open(self.kb_json_path, 'r', encoding='utf-8') as f:
                self.kb_data = json.load(f)
            logger.info(f"✅ Loaded KB JSON: {self.kb_json_path}")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON: {e}")
            sys.exit(1)

    def section(self, name: str) -> List[Dict[str, Any]]:
        """Resolve a KB section from the v0.1 layout (model.* / governance.*), falling back to a flat layout."""
        model = self.kb_data.get('model', {})
        governance = self.kb_data.get('governance', {})
        lookup = {
            'evidence_types': model.get('evidence_types'),
            'decision_types': model.get('decisions'),
            'verbs': model.get('verbs'),
            'links': model.get('links'),
            'governance_rules': governance.get('rules'),
            'entitlements': governance.get('entitlements'),
        }
        items = lookup.get(name)
        if items is None:
            items = self.kb_data.get(name, [])
        if not items:
            logger.warning(f"⚠️  KB section '{name}' is empty — nothing to insert")
        return items
    
    def insert_kb_version(self):
        """Insert KB version record"""
        query = """
            INSERT INTO ontology.kb_version (version, content_json, is_active, description)
            VALUES (%s, %s, %s, %s)
            RETURNING kb_version_id;
        """
        
        params = (
            self.kb_version,
            Json(self.kb_data),
            self.kb_active,
            f"Accord Retail KB v{self.kb_version}"
        )
        
        cursor = self.db.execute(query, params)
        self.kb_version_id = cursor.fetchone()[0]
        logger.info(f"✅ Inserted kb_version: {self.kb_version_id}")
    
    def insert_evidence_types(self):
        """Insert 20 evidence types"""
        evidence_types = self.section('evidence_types')
        
        query = """
            INSERT INTO ontology.kb_evidence_type 
            (kb_version_id, name, category, asserted_by, source_system, role_in_diagnosis, unit, calculation, confidence_factors, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        count = 0
        for et in evidence_types:
            params = (
                self.kb_version_id,
                et.get('name'),
                et.get('category'),
                et.get('asserted_by'),
                et.get('source_system'),
                et.get('role_in_diagnosis'),
                et.get('unit'),
                et.get('calculation'),
                Json(et.get('confidence_factors', {})),
                et.get('description')
            )
            self.db.execute(query, params)
            count += 1
        
        logger.info(f"✅ Inserted {count} evidence types")
    
    def insert_decision_types(self):
        """Insert 2 decision types"""
        decision_types = self.section('decision_types')
        
        query = """
            INSERT INTO ontology.kb_decision_type
            (kb_version_id, name, subject, question, reads_evidence_types, outcomes, logic_json, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        count = 0
        for dt in decision_types:
            params = (
                self.kb_version_id,
                dt.get('name'),
                dt.get('subject'),
                dt.get('question'),
                dt.get('reads_evidence_types') or dt.get('reads', []),
                [o.get('outcome') if isinstance(o, dict) else o for o in dt.get('outcomes', [])],
                Json({
                    'outcomes': dt.get('outcomes', []),
                    'always_returns': dt.get('always_returns', []),
                    'determinism': dt.get('determinism'),
                    'owner': dt.get('owner'),
                    'phase': dt.get('phase'),
                }),
                dt.get('description') or dt.get('determinism')
            )
            self.db.execute(query, params)
            count += 1
        
        logger.info(f"✅ Inserted {count} decision types")
    
    def insert_verbs(self):
        """Insert 8 verbs"""
        verbs = self.section('verbs')
        
        query = """
            INSERT INTO ontology.kb_verb
            (kb_version_id, name, label, mutates, performed_by, entitled_by, phase, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        count = 0
        for verb in verbs:
            params = (
                self.kb_version_id,
                verb.get('name'),
                verb.get('label'),
                verb.get('mutates'),
                verb.get('performed_by'),
                verb.get('entitled_by'),
                verb.get('phase'),
                verb.get('description')
            )
            self.db.execute(query, params)
            count += 1
        
        logger.info(f"✅ Inserted {count} verbs")
    
    def insert_links(self):
        """Insert object relationships"""
        links = self.section('links')
        
        query = """
            INSERT INTO ontology.kb_link
            (kb_version_id, link_name, from_object, to_objects, cardinality, meaning)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        count = 0
        for link in links:
            params = (
                self.kb_version_id,
                link.get('link') or link.get('name'),
                link.get('from') or link.get('from_object'),
                (lambda t: t if isinstance(t, list) else [t])(link.get('to') or link.get('to_objects') or []),
                link.get('cardinality'),
                link.get('meaning')
            )
            self.db.execute(query, params)
            count += 1
        
        logger.info(f"✅ Inserted {count} links")
    
    def insert_governance_rules(self):
        """Insert governance rules"""
        rules = self.section('governance_rules')
        
        query = """
            INSERT INTO ontology.kb_governance_rule
            (kb_version_id, rule_name, enforcement, phase)
            VALUES (%s, %s, %s, %s)
        """
        
        count = 0
        for rule in rules:
            params = (
                self.kb_version_id,
                (f"{rule['id']}  {rule['rule']}" if rule.get('id') and rule.get('rule') else rule.get('rule') or rule.get('name')),
                rule.get('enforcement'),
                rule.get('phase')
            )
            self.db.execute(query, params)
            count += 1
        
        logger.info(f"✅ Inserted {count} governance rules")
    
    def insert_entitlements(self):
        """Insert access control entitlements"""
        entitlements = self.section('entitlements')
        
        query = """
            INSERT INTO ontology.kb_entitlement
            (kb_version_id, role, can_perform, cannot_perform, scope)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        count = 0
        for ent in entitlements:
            params = (
                self.kb_version_id,
                ent.get('role'),
                ent.get('can_perform'),
                ent.get('cannot_perform'),
                ent.get('scope')
            )
            self.db.execute(query, params)
            count += 1
        
        logger.info(f"✅ Inserted {count} entitlements")
    
    def run(self):
        """Load entire KB"""
        logger.info("=" * 80)
        logger.info("Starting Accord Retail KB Load")
        logger.info("=" * 80)
        
        try:
            self.load_kb_json()
            self.insert_kb_version()
            self.insert_evidence_types()
            self.insert_decision_types()
            self.insert_verbs()
            self.insert_links()
            self.insert_governance_rules()
            self.insert_entitlements()
            
            self.db.commit()
            
            logger.info("=" * 80)
            logger.info("✅ KB LOAD SUCCESSFUL")
            logger.info("=" * 80)
            logger.info(f"KB Version ID: {self.kb_version_id}")
            logger.info(f"KB Version: {self.kb_version}")
            logger.info(f"Active: {self.kb_active}")
            
        except Exception as e:
            logger.error(f"❌ KB Load failed: {e}")
            sys.exit(1)

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description='Load Accord Retail KB JSON into PostgreSQL'
    )
    parser.add_argument(
        '--env',
        type=str,
        default='.env',
        help='Path to .env file (default: .env)'
    )
    parser.add_argument(
        '--kb-json',
        type=str,
        default=None,
        help='Path to KB JSON file (overrides env variable)'
    )
    parser.add_argument(
        '--kb-version',
        type=str,
        default=None,
        help='KB version (overrides env variable)'
    )
    parser.add_argument(
        '--active',
        action='store_true',
        help='Mark KB as active'
    )
    
    args = parser.parse_args()
    
    # Load .env file
    if HAS_DOTENV:
        load_dotenv(args.env)
        logger.info(f"✅ Loaded environment from {args.env}")
    else:
        logger.warning("⚠️  python-dotenv not installed, reading only from environment variables")
    
    # Get database configuration
    db_host = os.getenv('DATABASE_HOST')
    db_port = int(os.getenv('DATABASE_PORT', 5432))
    db_user = os.getenv('DATABASE_USER')
    db_password = os.getenv('DATABASE_PASSWORD')
    db_name = os.getenv('DATABASE_NAME')
    
    if not all([db_host, db_user, db_password, db_name]):
        logger.error("❌ Missing required database environment variables")
        logger.error("   Required: DATABASE_HOST, DATABASE_USER, DATABASE_PASSWORD, DATABASE_NAME")
        sys.exit(1)
    
    # Get KB configuration
    kb_json_path = args.kb_json or os.getenv('KB_JSON_PATH', 'ontology/accord_retail_ontology_kb.json')
    kb_version = args.kb_version or os.getenv('KB_VERSION', '0.1')
    kb_active = args.active or os.getenv('KB_ACTIVE', 'false').lower() == 'true'
    
    # Validate KB JSON file exists
    if not os.path.exists(kb_json_path):
        logger.error(f"❌ KB JSON file not found: {kb_json_path}")
        logger.error("   Please provide path to accord_retail_ontology_kb.json")
        sys.exit(1)
    
    # Check if psycopg2 is installed
    if not HAS_PSYCOPG2:
        logger.error("❌ psycopg2 not installed")
        logger.error("   Install with: pip install psycopg2-binary")
        sys.exit(1)
    
    # Connect to database
    db = DBConnection(db_host, db_port, db_user, db_password, db_name)
    db.connect()
    
    # Load KB
    loader = KBLoader(db, kb_json_path, kb_version, kb_active)
    loader.run()
    
    # Close connection
    db.close()
    
    logger.info("✅ Done!")

# ============================================================================

if __name__ == '__main__':
    main()
