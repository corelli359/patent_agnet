import { Link } from 'react-router-dom';
import './Home.css';

function Home() {
    const highlights = [
        {
            id: 'workspace',
            title: '项目工作台',
            desc: '围绕单一专利项目查看阶段进度、风险、检索证据、交付物和下一步动作，是现在的主入口。',
            status: '推荐入口',
            link: '/workspace'
        },
    ];

    const skills = [
        {
            id: 1,
            title: '发明意图总结',
            desc: '通过多轮AI对话引导，将碎片化的技术创意转化为结构化的发明意图文档',
            status: '✅ 可用',
            link: '/skill1'
        },
        {
            id: 2,
            title: '技术交底书撰写',
            desc: '基于发明意图自动生成符合《专利审查指南》规范的技术交底书',
            status: '✅ 可用',
            link: '/skill2'
        },
        {
            id: 3,
            title: '专利申请文件起草',
            desc: '生成正式的专利申请文件：权利要求书、说明书、摘要',
            status: '✅ 可用',
            link: '/skill3'
        },
        {
            id: 4,
            title: '实质审查模拟',
            desc: '模拟审查员视角，进行形式、新颖性、创造性、清楚性审查',
            status: '✅ 可用',
            link: '/skill4'
        },
        {
            id: 5,
            title: '专利修复',
            desc: '解析审查意见，生成修改方案，自动撰写答复意见书',
            status: '✅ 可用',
            link: '/skill5'
        },
        {
            id: 6,
            title: '专利检索与分析',
            desc: 'Google Patents检索，关键词分析、IPC分类、新颖性评估',
            status: '✅ 可用',
            link: '/skill6'
        }
    ];

    const cards = [...highlights, ...skills];

    return (
        <div className="home">
            <div className="hero">
                <h1>专利全流程产出系统</h1>
                <p>从创意澄清、检索分析到申请文件与交付包，围绕单一项目推进完整专利链路。</p>
                <div className="progress-bar">
                    <div className="progress-fill" style={{ width: '92%' }}></div>
                </div>
                <p className="progress-text">当前重点: 项目级工作台已上线，后续继续增强检索深度与前端闭环</p>
            </div>

            <div className="workflow">
                <h2>完整工作流程</h2>
                <div className="workflow-steps">
                    {skills.map((skill, index) => (
                        <div key={skill.id} className="workflow-item">
                            <div className="workflow-step">{skill.title}</div>
                            {index < skills.length - 1 && <div className="workflow-arrow">→</div>}
                        </div>
                    ))}
                </div>
            </div>

            <div className="skills-grid">
                {cards.map(skill => (
                    <Link to={skill.link} key={skill.id} className="skill-card">
                        <div className="skill-number">{typeof skill.id === 'number' ? skill.id : 'W'}</div>
                        <h3 className="skill-title">{skill.title}</h3>
                        <p className="skill-desc">{skill.desc}</p>
                        <div className="skill-status">{skill.status}</div>
                    </Link>
                ))}
            </div>

            <div className="api-info">
                <h3>API 信息</h3>
                <p><strong>后端服务</strong>: http://localhost:8000</p>
                <p><strong>API文档</strong>: <a href="http://localhost:8000/docs" target="_blank">Swagger UI</a></p>
            </div>
        </div>
    );
}

export default Home;
