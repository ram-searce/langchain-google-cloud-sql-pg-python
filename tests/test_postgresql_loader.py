# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os

import pytest
import pytest_asyncio
from langchain_core.documents import Document

from src.langchain_google_cloud_sql_pg import PostgreSQLLoader, PostgreSQLDocumentSaver, PostgreSQLEngine, Column

project_id = os.environ["PROJECT_ID"]
region = os.environ["REGION"]
instance_id = os.environ["INSTANCE_ID"]
db_name = os.environ["DB_NAME"]
table_name = os.environ["TABLE_NAME"]


@pytest.mark.asyncio
class TestLoaderAsync:

    @pytest_asyncio.fixture
    async def engine(self):
        engine = await PostgreSQLEngine.afrom_instance(
            project_id=project_id,
            instance=instance_id,
            region=region,
            database=db_name,
        )
        yield engine

    async def _collect_async_items(self, docs_generator):
        """Collects items from an async generator."""
        docs = []
        async for doc in docs_generator:
            docs.append(doc)
        return docs

    async def _cleanup_table(self, engine):
        query = f"DROP TABLE IF EXISTS {table_name}"
        await engine._aexecute(query)

    async def test_load_from_query_default(self, engine):
        try:
            await self._cleanup_table(engine)
            query = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        fruit_id SERIAL PRIMARY KEY,
                        fruit_name VARCHAR(100) NOT NULL,
                        variety VARCHAR(50),
                        quantity_in_stock INT NOT NULL,
                        price_per_unit INT NOT NULL,
                        organic INT NOT NULL
                    )
                """
            await engine._aexecute(query)

            insert_query = f"""
                INSERT INTO {table_name} (
                    fruit_name, variety, quantity_in_stock, price_per_unit, organic
                ) VALUES ('Apple', 'Granny Smith', 150, 1, 1);
            """
            await engine._aexecute(insert_query)

            loader = PostgreSQLLoader(
                engine=engine,
                query=f"SELECT * FROM {table_name};",
                table_name=table_name,
            )

            documents = await self._collect_async_items(loader.alazy_load())

            assert documents == [
                Document(
                    page_content="1",
                    metadata={
                        "fruit_name": "Apple",
                        "variety": "Granny Smith",
                        "quantity_in_stock": 150,
                        "price_per_unit": 1,
                        "organic": 1,
                    },
                )
            ]

        finally:
            await self._cleanup_table(engine)

    async def test_load_from_query_customized_content_customized_metadata(self, engine):
        try:
            await self._cleanup_table(engine)
            query = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        fruit_id SERIAL PRIMARY KEY,
                        fruit_name VARCHAR(100) NOT NULL,
                        variety VARCHAR(50),
                        quantity_in_stock INT NOT NULL,
                        price_per_unit INT NOT NULL,
                        organic INT NOT NULL
                    )
                """
            await engine._aexecute(query)

            insert_query = f"""
                INSERT INTO {table_name} (fruit_name, variety, quantity_in_stock, price_per_unit, organic)
                VALUES ('Apple', 'Granny Smith', 150, 0.99, 1),
                       ('Banana', 'Cavendish', 200, 0.59, 0),
                       ('Orange', 'Navel', 80, 1.29, 1);
            """
            await engine._aexecute(insert_query)

            loader = PostgreSQLLoader(
                engine=engine,
                query=f'SELECT * FROM "{table_name}";',
                content_columns=[
                    "fruit_name",
                    "variety",
                    "quantity_in_stock",
                    "price_per_unit",
                    "organic",
                ],
                metadata_columns=["fruit_id"],
            )

            documents = await self._collect_async_items(loader.alazy_load())

            assert documents == [
                Document(
                    page_content="Apple Granny Smith 150 1 1",
                    metadata={"fruit_id": 1},
                ),
                Document(
                    page_content="Banana Cavendish 200 1 0",
                    metadata={"fruit_id": 2},
                ),
                Document(
                    page_content="Orange Navel 80 1 1",
                    metadata={"fruit_id": 3},
                ),
            ]

        finally:
            await self._cleanup_table(engine)

    async def test_load_from_query_customized_content_default_metadata(self, engine):
        try:
            await self._cleanup_table(engine)
            query = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        fruit_id SERIAL PRIMARY KEY,
                        fruit_name VARCHAR(100) NOT NULL,
                        variety VARCHAR(50),
                        quantity_in_stock INT NOT NULL,
                        price_per_unit INT NOT NULL,
                        organic INT NOT NULL
                    )
                """
            await engine._aexecute(query)

            insert_query = f"""
                INSERT INTO {table_name} (fruit_name, variety, quantity_in_stock, price_per_unit, organic)
                VALUES ('Apple', 'Granny Smith', 150, 1, 1);
            """
            await engine._aexecute(insert_query)

            loader = PostgreSQLLoader(
                engine=engine,
                query=f'SELECT * FROM "{table_name}";',
                content_columns=[
                    "variety",
                    "quantity_in_stock",
                    "price_per_unit",
                ],
            )

            documents = await self._collect_async_items(loader.alazy_load())

            assert documents == [
                Document(
                    page_content="Granny Smith 150 1",
                    metadata={
                        "fruit_id": 1,
                        "fruit_name": "Apple",
                        "organic": 1,
                    },
                )
            ]

        finally:
            await self._cleanup_table(engine)

    async def test_load_from_query_default_content_customized_metadata(self, engine):
        try:
            await self._cleanup_table(engine)
            query = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        fruit_id SERIAL PRIMARY KEY,
                        fruit_name VARCHAR(100) NOT NULL,
                        variety VARCHAR(50),
                        quantity_in_stock INT NOT NULL,
                        price_per_unit INT NOT NULL,
                        organic INT NOT NULL
                    )
                """
            await engine._aexecute(query)

            insert_query = f"""
                        INSERT INTO {table_name} (
                            fruit_name,
                            variety,
                            quantity_in_stock,
                            price_per_unit,
                            organic
                        ) VALUES ('Apple', 'Granny Smith', 150, 1, 1);
            """
            await engine._aexecute(insert_query)

            loader = PostgreSQLLoader(
                engine=engine,
                query=f'SELECT * FROM "{table_name}";',
                metadata_columns=["fruit_name", "organic"],
            )

            documents = await self._collect_async_items(loader.alazy_load())

            assert documents == [
                Document(
                    page_content="1",
                    metadata={"fruit_name": "Apple", "organic": 1},
                )
            ]

        finally:
            await self._cleanup_table(engine)

    async def test_load_from_query_with_langchain_metadata(self, engine):
        try:
            await self._cleanup_table(engine)
            query = f"""
                CREATE TABLE IF NOT EXISTS {table_name}(
                    fruit_id SERIAL PRIMARY KEY,
                    fruit_name VARCHAR(100) NOT NULL,
                    variety VARCHAR(50),
                    quantity_in_stock INT NOT NULL,
                    price_per_unit INT NOT NULL,
                    langchain_metadata JSON NOT NULL
                )
                """
            await engine._aexecute(query)

            metadata = json.dumps({"organic": 1})
            insert_query = f"""
                INSERT INTO {table_name} 
                (fruit_name, variety, quantity_in_stock, price_per_unit, langchain_metadata) 
                VALUES ('Apple', 'Granny Smith', 150, 1, '{metadata}');"""
            await engine._aexecute(insert_query)

            loader = PostgreSQLLoader(
                engine=engine,
                query=f'SELECT * FROM "{table_name}";',
                metadata_columns=[
                    "fruit_name",
                    "langchain_metadata",
                ],
            )

            documents = await self._collect_async_items(loader.alazy_load())

            assert documents == [
                Document(
                    page_content="1",
                    metadata={
                        "fruit_name": "Apple",
                        "organic": 1,
                    }
                )
            ]

        finally:
            await self._cleanup_table(engine)

    async def test_load_from_query_customized_content_default_metadata_custom_formatter(self, engine):
        try:
            await self._cleanup_table(engine)
            query = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        fruit_id SERIAL PRIMARY KEY,
                        fruit_name VARCHAR(100) NOT NULL,
                        variety VARCHAR(50),
                        quantity_in_stock INT NOT NULL,
                        price_per_unit INT NOT NULL,
                        organic INT NOT NULL
                    )
                """
            await engine._aexecute(query)

            insert_query = f"""
                        INSERT INTO {table_name} (fruit_name, variety, quantity_in_stock, price_per_unit, organic)
                        VALUES ('Apple', 'Granny Smith', 150, 1, 1);
                        """
            await engine._aexecute(insert_query)

            def my_formatter(**kwargs):
                return '-'.join(kwargs.values())
                # return '--'.join(f"{k}:{v}" for k,v in kwargs.items())

            loader = PostgreSQLLoader(
                engine=engine,
                query=f'SELECT * FROM "{table_name}";',
                content_columns=[
                    "variety",
                    "quantity_in_stock",
                    "price_per_unit",
                ],
                formatter=my_formatter,
            )

            documents = await self._collect_async_items(loader.alazy_load())

            assert documents == [
                Document(
                    page_content="Granny Smith-150-1",
                    metadata={
                        "fruit_id": 1,
                        "fruit_name": "Apple",
                        "organic": 1,
                    },
                )
            ]

        finally:
            await self._cleanup_table(engine)

    async def test_load_from_query_customized_content_default_metadata_custom_page_content_format(self, engine):
        try:
            await self._cleanup_table(engine)
            query = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        fruit_id SERIAL PRIMARY KEY,
                        fruit_name VARCHAR(100) NOT NULL,
                        variety VARCHAR(50),
                        quantity_in_stock INT NOT NULL,
                        price_per_unit INT NOT NULL,
                        organic INT NOT NULL
                    )
                """
            await engine._aexecute(query)

            insert_query = f"""
                            INSERT INTO {table_name} (fruit_name, variety, quantity_in_stock, price_per_unit, organic)
                            VALUES ('Apple', 'Granny Smith', 150, 1, 1);
                        """
            await engine._aexecute(insert_query)

            loader = PostgreSQLLoader(
                engine=engine,
                query=f'SELECT * FROM "{table_name}";',
                content_columns=[
                    "variety",
                    "quantity_in_stock",
                    "price_per_unit",
                ],
                format="yaml",
            )

            documents = await self._collect_async_items(loader.alazy_load())

            assert documents == [
                Document(
                    page_content="variety:Granny Smith\nquantity_in_stock:150\nprice_per_unit:1",
                    metadata={
                        "fruit_id": 1,
                        "fruit_name": "Apple",
                        "organic": 1,
                    },
                )
            ]

        finally:
            await self._cleanup_table(engine)

    async def test_save_doc_with_default_metadata(self, engine):
        try:
            await engine.init_document_table(table_name)
            test_docs = [
                Document(
                    page_content="Apple Granny Smith 150 0.99 1",
                    metadata={"fruit_id": 1},
                ),
                Document(
                    page_content="Banana Cavendish 200 0.59 0",
                    metadata={"fruit_id": 2},
                ),
                Document(
                    page_content="Orange Navel 80 1.29 1",
                    metadata={"fruit_id": 3},
                ),
            ]
            saver = PostgreSQLDocumentSaver(engine=engine, table_name=table_name)
            loader = PostgreSQLLoader(engine=engine, table_name=table_name)

            await saver.aadd_documents(test_docs)
            docs = await self._collect_async_items(loader.alazy_load())

            assert docs == test_docs
            assert (await engine._load_document_table(table_name)).columns.keys() == [
                "page_content",
                "langchain_metadata",
            ]
        finally:
            await self._cleanup_table(engine)

    @pytest.mark.parametrize("store_metadata", [True, False])
    async def test_save_doc_with_customized_metadata(self, engine, store_metadata):

        await engine.init_document_table(
            table_name,
            metadata_columns=[
                Column(
                    "fruit_name",
                    "VARCHAR"
                ),
                Column(
                    "organic",
                    "BOOLEAN"
                ),
            ],
            store_metadata=store_metadata,
        )
        test_docs = [
            Document(
                page_content="Granny Smith 150 0.99",
                metadata={"fruit_id": 1, "fruit_name": "Apple", "organic": True},
            ),
        ]
        saver = PostgreSQLDocumentSaver(engine=engine, table_name=table_name)
        loader = PostgreSQLLoader(
            engine=engine,
            table_name=table_name,
            metadata_columns=[
                "fruit_id",
                "fruit_name",
                "organic",
            ],
        )

        await saver.aadd_documents(test_docs)
        docs = await self._collect_async_items(loader.alazy_load())

        if store_metadata:
            docs == test_docs
            assert (await engine._load_document_table(table_name)).columns.keys() == [
                "page_content",
                "fruit_name",
                "organic",
                "langchain_metadata",
            ]
        else:
            assert docs == [
                Document(
                    page_content="Granny Smith 150 0.99",
                    metadata={"fruit_name": "Apple", "organic": True},
                ),
            ]
            assert (await engine._load_document_table(table_name)).columns.keys() == [
                "page_content",
                "fruit_name",
                "organic",
            ]

    async def test_save_doc_without_metadata(self, engine):

        try:

            await engine.init_document_table(
                table_name,
                metadata_json_columns=None,
                store_metadata=False
            )
            test_docs = [
                Document(
                    page_content="Granny Smith 150 0.99",
                    metadata={"fruit_id": 1, "fruit_name": "Apple", "organic": 1},
                ),

            ]
            saver = PostgreSQLDocumentSaver(engine=engine, table_name=table_name)
            await saver.aadd_documents(test_docs)

            loader = PostgreSQLLoader(
                engine=engine,
                table_name=table_name,
            )

            docs = await self._collect_async_items(loader.alazy_load())

            assert docs == [
                Document(
                    page_content="Granny Smith 150 0.99",
                    metadata={},
                ),
            ]
            assert (await engine._load_document_table(table_name)).columns.keys() == [
                "page_content",
            ]
        finally:
            await self._cleanup_table(engine)

    async def test_delete_doc_with_default_metadata(self, engine):
        await engine.init_document_table(table_name)

        try:
            test_docs = [
                Document(
                    page_content="Apple Granny Smith 150 0.99 1",
                    metadata={"fruit_id": 1},
                ),
                Document(
                    page_content="Banana Cavendish 200 0.59 0 1",
                    metadata={"fruit_id": 2},
                ),
            ]
            saver = PostgreSQLDocumentSaver(engine=engine, table_name=table_name)
            loader = PostgreSQLLoader(engine=engine, table_name=table_name)

            await saver.aadd_documents(test_docs)
            docs = await self._collect_async_items(loader.alazy_load())
            assert docs == test_docs

            await saver.adelete(docs[:1])
            assert len(await self._collect_async_items(loader.alazy_load())) == 1

            await saver.adelete(docs)
            assert len(await self._collect_async_items(loader.alazy_load())) == 0
        finally:
            await self._cleanup_table(engine)

    async def test_delete_doc_with_query(self, engine):
        await self._cleanup_table(engine)

        await engine.init_document_table(
            table_name,
            metadata_columns=[
                Column(
                    "fruit_name",
                    "VARCHAR",
                ),
                Column(
                    "organic",
                    "BOOLEAN",
                ),
            ],
            store_metadata=True,
        )

        try:
            test_docs = [
                Document(
                    page_content="Granny Smith 150 0.99",
                    metadata={"fruit-id": 1, "fruit_name": "Apple", "organic": True},
                ),
                Document(
                    page_content="Cavendish 200 0.59 0",
                    metadata={"fruit_id": 2, "fruit_name": "Banana", "organic": False},
                ),
                Document(
                    page_content="Navel 80 1.29 1",
                    metadata={"fruit_id": 3, "fruit_name": "Orange", "organic": True},
                ),
            ]
            saver = PostgreSQLDocumentSaver(engine=engine, table_name=table_name)
            # loader = PostgreSQLLoader(engine=engine, table_name=table_name)
            query = f"select * from {table_name} where fruit_name='Apple';"
            loader = PostgreSQLLoader(engine=engine, query=query)

            await saver.aadd_documents(test_docs)
            docs = await self._collect_async_items(loader.alazy_load())
            assert len(docs) == 1

            await saver.adelete(docs)
            assert len(await self._collect_async_items(loader.alazy_load())) == 0
        finally:
            await self._cleanup_table(engine)

    @pytest.mark.parametrize("metadata_json_column", [None, "metadata_col_test"])
    async def test_delete_doc_with_customized_metadata(self, engine, metadata_json_column):

        # TODO Partial Implementation

        content_column = "content_col_test"
        engine.init_document_table(
            table_name,
            metadata_columns=[
                Column(
                    "fruit_name",
                    "VARCHAR"
                ),
                Column(
                    "organic",
                    "BOOLEAN"
                ),
            ],
            content_column=content_column,
            metadata_json_column=metadata_json_column,
        )
        test_docs = [
            Document(
                page_content="Granny Smith 150 0.99",
                metadata={"fruit-id": 1, "fruit_name": "Apple", "organic": True},
            ),
            Document(
                page_content="Cavendish 200 0.59 0",
                metadata={"fruit_id": 2, "fruit_name": "Banana", "organic": True},
            ),
        ]
        saver = PostgreSQLDocumentSaver(
            engine=engine,
            table_name=table_name,
            content_column=content_column,
            metadata_json_column=metadata_json_column,
        )
        loader = PostgreSQLLoader(
            engine=engine,
            table_name=table_name,
            content_columns=[content_column],
            metadata_json_column=metadata_json_column,
        )

        await saver.aadd_documents(test_docs)
        docs = loader.load()
        assert len(docs) == 2

        await saver.adelete(docs[:1])
        assert len(await self._collect_async_items(loader.alazy_load())) == 1

        await saver.adelete(docs)
        assert len(await self._collect_async_items(loader.alazy_load())) == 0

    def test_sync_engine(self):
        engine = PostgreSQLEngine.from_instance(
            project_id=project_id,
            instance=instance_id,
            region=region,
            database=db_name,
        )
        assert engine