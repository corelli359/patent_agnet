    def _build_query_description(
        self,
        keywords: Optional[List[Dict[str, str]]],
        ipc_classes: Optional[List[str]],
        cpc_classes: Optional[List[str]]
    ) -> str:
        """构建查询描述（用于日志和历史）"""
        parts = []
        
        if keywords:
            kw_parts = []
            for kw in keywords:
                term = kw.get('term', '')
                scope = kw.get('scope', 'TAC')
                scope_name = {
                    'TI': '标题',
                    'AB': '摘要',
                    'CL': '权利要求',
                    'TAC': '全文'
                }.get(scope, '全文')
                kw_parts.append(f'"{term}"({scope_name})')
            parts.append('关键词:' + '+'.join(kw_parts))
        
        if ipc_classes:
            parts.append(f'IPC:{",".join(ipc_classes)}')
        
        if cpc_classes:
            parts.append(f'CPC:{",".join(cpc_classes)}')
        
        return ' '.join(parts) if parts else '空查询'
