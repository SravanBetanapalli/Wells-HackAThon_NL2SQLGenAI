"""Summarizer Agent for providing insights about query results"""
from typing import Dict, Any, List
import pandas as pd
from .metadata_loader import MetadataLoader
from .logger_config import log_agent_flow

class SummarizerAgent:
    def __init__(self, max_preview: int = 5):
        self.max_preview = max_preview
        self.metadata_loader = MetadataLoader()

    @log_agent_flow("SummarizerAgent")
    def summarize(self, query: str, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights from query results"""
        if not execution_result.get("success", False):
            return {
                "summary": f"⚠️ **Query Failed**\n\n**Your Question:** {query}\n\n**Error:** {execution_result.get('error')}",
                "suggestions": [
                    "Try rephrasing your question",
                    "Check if the table names are correct",
                    "Make sure you're asking about existing data"
                ]
            }

        results = execution_result.get("results", [])
        if not results:
            return {
                "summary": f"❌ **No Results Found**\n\n**Your Question:** {query}\n\nNo data matches your criteria. Try refining your search or ask a different question.",
                "suggestions": [
                    "Try broadening your search criteria",
                    "Check if the data exists in the database",
                    "Try a different time period or category"
                ]
            }

        # Convert results to DataFrame for analysis
        df = pd.DataFrame(results)
        total_rows = len(df)
        
        # Get query context
        query_lower = query.lower()
        
        # Branch-related insights
        if "branch" in query_lower:
            return self._generate_branch_insights(query, df)
            
        # Employee-related insights
        elif "employee" in query_lower or "salary" in query_lower:
            return self._generate_employee_insights(query, df)
            
        # Account-related insights
        elif "account" in query_lower or "balance" in query_lower:
            return self._generate_account_insights(query, df)
            
        # Transaction-related insights
        elif "transaction" in query_lower:
            return self._generate_transaction_insights(query, df)
            
        # Generic insights
        return self._generate_generic_insights(query, df)

    def _generate_branch_insights(self, query: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate insights for branch-related queries"""
        total_branches = len(df)
        
        summary_parts = [
            f"📊 **Branch Analysis**\n\n**Your Question:** {query}\n",
            f"Found **{total_branches}** {'branch' if total_branches == 1 else 'branches'}."
        ]

        # Add manager statistics if available
        if 'manager_name' in df.columns:
            managed_count = df['manager_name'].notna().sum()
            unmanaged_count = df['manager_name'].isna().sum()
            summary_parts.append(f"\n**Management Overview:**")
            summary_parts.append(f"• Branches with managers: **{managed_count}**")
            summary_parts.append(f"• Branches without managers: **{unmanaged_count}**")
            summary_parts.append(f"• Management coverage: **{(managed_count/total_branches)*100:.1f}%**")

        # Add state distribution if available
        if 'state' in df.columns:
            valid_states = self.metadata_loader.get_distinct_values('branches', 'state')
            state_counts = df['state'].value_counts()
            if not state_counts.empty:
                summary_parts.append("\n**State Distribution:**")
                for state in valid_states:
                    if state in state_counts:
                        summary_parts.append(f"• {state}: **{state_counts[state]}**")

        suggestions = [
            "Show me branches without managers",
            "Which branch has the most employees?",
            "Show me branch performance by transaction volume",
            "List branches by city"
        ]

        return {
            "summary": "\n".join(summary_parts),
            "suggestions": suggestions
        }

    def _generate_employee_insights(self, query: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate insights for employee-related queries"""
        total_employees = len(df)
        
        summary_parts = [
            f"👥 **Employee Analysis**\n\n**Your Question:** {query}\n",
            f"Found **{total_employees}** {'employee' if total_employees == 1 else 'employees'}."
        ]

        if 'salary' in df.columns:
            avg_salary = df['salary'].mean()
            max_salary = df['salary'].max()
            min_salary = df['salary'].min()
            summary_parts.extend([
                f"\n**Salary Statistics:**",
                f"• Average: **${avg_salary:,.2f}**",
                f"• Highest: **${max_salary:,.2f}**",
                f"• Lowest: **${min_salary:,.2f}**"
            ])

        if 'position' in df.columns:
            valid_positions = self.metadata_loader.get_distinct_values('employees', 'position')
            position_counts = df['position'].value_counts()
            summary_parts.extend([
                f"\n**Position Distribution:**"
            ])
            for pos in valid_positions:
                if pos in position_counts:
                    summary_parts.append(f"• {pos}: **{position_counts[pos]}**")

        suggestions = [
            "Show me the highest paid employees",
            "What's the average salary by position?",
            "Show me employees hired in the last year",
            "Which employees handle the most transactions?"
        ]

        return {
            "summary": "\n".join(summary_parts),
            "suggestions": suggestions
        }

    def _generate_account_insights(self, query: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate insights for account-related queries"""
        total_accounts = len(df)
        
        summary_parts = [
            f"💳 **Account Analysis**\n\n**Your Question:** {query}\n",
            f"Found **{total_accounts}** {'account' if total_accounts == 1 else 'accounts'}."
        ]

        if 'balance' in df.columns:
            total_balance = df['balance'].sum()
            avg_balance = df['balance'].mean()
            summary_parts.extend([
                f"\n**Balance Statistics:**",
                f"• Total Balance: **${total_balance:,.2f}**",
                f"• Average Balance: **${avg_balance:,.2f}**"
            ])

        if 'type' in df.columns:
            valid_types = self.metadata_loader.get_distinct_values('accounts', 'type')
            type_counts = df['type'].value_counts()
            summary_parts.extend([
                f"\n**Account Types:**"
            ])
            for acc_type in valid_types:
                if acc_type in type_counts:
                    summary_parts.append(f"• {acc_type}: **{type_counts[acc_type]}**")

        if 'status' in df.columns:
            valid_statuses = self.metadata_loader.get_distinct_values('accounts', 'status')
            status_counts = df['status'].value_counts()
            summary_parts.extend([
                f"\n**Account Status:**"
            ])
            for status in valid_statuses:
                if status in status_counts:
                    summary_parts.append(f"• {status}: **{status_counts[status]}**")

        suggestions = [
            "Show me accounts with high balances",
            "What's the average balance by account type?",
            "Show me recently opened accounts",
            "Which accounts have the most transactions?"
        ]

        return {
            "summary": "\n".join(summary_parts),
            "suggestions": suggestions
        }

    def _generate_transaction_insights(self, query: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate insights for transaction-related queries"""
        total_transactions = len(df)
        
        summary_parts = [
            f"💸 **Transaction Analysis**\n\n**Your Question:** {query}\n",
            f"Found **{total_transactions}** {'transaction' if total_transactions == 1 else 'transactions'}."
        ]

        if 'amount' in df.columns:
            total_amount = df['amount'].sum()
            avg_amount = df['amount'].mean()
            summary_parts.extend([
                f"\n**Amount Statistics:**",
                f"• Total Amount: **${total_amount:,.2f}**",
                f"• Average Amount: **${avg_amount:,.2f}**"
            ])

        if 'type' in df.columns:
            valid_types = self.metadata_loader.get_distinct_values('transactions', 'type')
            type_counts = df['type'].value_counts()
            summary_parts.extend([
                f"\n**Transaction Types:**"
            ])
            for tx_type in valid_types:
                if tx_type in type_counts:
                    summary_parts.append(f"• {tx_type}: **{type_counts[tx_type]}**")

        if 'status' in df.columns:
            valid_statuses = self.metadata_loader.get_distinct_values('transactions', 'status')
            status_counts = df['status'].value_counts()
            summary_parts.extend([
                f"\n**Transaction Status:**"
            ])
            for status in valid_statuses:
                if status in status_counts:
                    summary_parts.append(f"• {status}: **{status_counts[status]}**")

        suggestions = [
            "Show me high-value transactions",
            "What's the average transaction amount by type?",
            "Show me today's transactions",
            "Which accounts have the most transactions?"
        ]

        return {
            "summary": "\n".join(summary_parts),
            "suggestions": suggestions
        }

    def _generate_generic_insights(self, query: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate insights for general queries"""
        total_rows = len(df)
        
        summary_parts = [
            f"📊 **Query Results**\n\n**Your Question:** {query}\n",
            f"Found **{total_rows}** {'result' if total_rows == 1 else 'results'}."
        ]

        # Add column statistics
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
        if len(numeric_cols) > 0:
            summary_parts.append("\n**Numeric Column Statistics:**")
            for col in numeric_cols[:3]:  # Show stats for up to 3 numeric columns
                avg = df[col].mean()
                max_val = df[col].max()
                min_val = df[col].min()
                summary_parts.append(f"• {col}:")
                summary_parts.append(f"  - Average: **{avg:,.2f}**")
                summary_parts.append(f"  - Range: **{min_val:,.2f}** to **{max_val:,.2f}**")

        # Add categorical column distributions
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols[:2]:  # Show distributions for up to 2 categorical columns
            value_counts = df[col].value_counts()
            if not value_counts.empty:
                summary_parts.append(f"\n**{col} Distribution:**")
                for val, count in value_counts.head(3).items():
                    summary_parts.append(f"• {val}: **{count}**")

        suggestions = [
            "Show me the count of rows by table",
            "What are the most common values?",
            "Show me the data distribution",
            "Can you explain the patterns in this data?"
        ]

        return {
            "summary": "\n".join(summary_parts),
            "suggestions": suggestions
        }