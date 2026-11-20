import React, { useEffect, useState } from 'react';
import { getAdminAgentConfig, updateAdminAgentConfig } from '../../api/client';
import { errorKey } from '../../locales/messages';
import { useRequest } from '../materials/useRequest';
import AdminPanel from './AdminPanel';

export default function AgentConfigPanel({ token, t }) {
  const agent = useRequest(signal => getAdminAgentConfig(token, signal), [token]);
  const [model, setModel] = useState('');
  const [maxTokens, setMaxTokens] = useState(800);
  const [temperature, setTemperature] = useState(0.3);
  const [toolsEnabled, setToolsEnabled] = useState(true);
  const [maxToolSteps, setMaxToolSteps] = useState(4);
  const [enabledTools, setEnabledTools] = useState([]);
  const [systemPrompt, setSystemPrompt] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const cfg = agent.data;
    if (!cfg) return;
    setModel(cfg.model);
    setMaxTokens(cfg.max_tokens);
    setTemperature(cfg.temperature);
    setToolsEnabled(Boolean(cfg.tools_enabled));
    setMaxToolSteps(cfg.max_tool_steps);
    setEnabledTools(cfg.enabled_tools || []);
    setSystemPrompt(cfg.system_prompt || '');
  }, [agent.data]);

  function toggleTool(toolName) {
    setEnabledTools(current => current.includes(toolName)
      ? current.filter(item => item !== toolName)
      : [...current, toolName]);
  }

  async function save(event) {
    event.preventDefault();
    setSaving(true); setMessage(''); setError('');
    try {
      await updateAdminAgentConfig({
        model: model.trim(),
        max_tokens: Number(maxTokens),
        temperature: Number(temperature),
        tools_enabled: toolsEnabled,
        max_tool_steps: Number(maxToolSteps),
        enabled_tools: enabledTools,
        system_prompt: systemPrompt,
      }, token);
      setMessage(t('admin.agentSaved'));
      agent.retry();
    } catch (err) {
      setError(err.message || t(errorKey(err)));
    } finally {
      setSaving(false);
    }
  }

  return <AdminPanel id="admin-agent" title={t('admin.agent')} request={agent} t={t}>{data => <>
    <p className="admin-help">{t('admin.agentHelp')}</p>
    <p className={data.api_key_configured ? 'status-pill on' : 'status-pill'}>
      {data.api_key_configured
        ? `${t('admin.agentKeyOn')} (${data.provider === 'inception' ? 'Inception Labs' : 'Anthropic'})`
        : t('admin.agentKeyOff')}
    </p>
    <form className="admin-config-form" onSubmit={save}>
      <div className="admin-grid-3">
        <label>{t('admin.agentModel')}
          <input list="agent-model-presets" value={model} onChange={e => setModel(e.target.value)} maxLength={100} required/>
          <datalist id="agent-model-presets">
            <option value="mercury-2"/>
            <option value="mercury-2.5"/>
            <option value="mercury-3"/>
            <option value="claude-sonnet-5-5"/>
          </datalist>
        </label>
        <label>{t('admin.agentMaxTokens')}
          <input type="number" min={64} max={4000} value={maxTokens} onChange={e => setMaxTokens(e.target.value)} required/>
        </label>
        <label>{t('admin.agentTemperature')}
          <input type="number" min={0} max={1} step={0.1} value={temperature} onChange={e => setTemperature(e.target.value)} required/>
        </label>
      </div>
      <div className="admin-grid-2">
        <label className="check">
          <input type="checkbox" checked={toolsEnabled} onChange={e => setToolsEnabled(e.target.checked)}/>
          {t('admin.agentToolsToggle')}
        </label>
        <label>{t('admin.agentMaxSteps')}
          <input type="number" min={1} max={8} value={maxToolSteps} onChange={e => setMaxToolSteps(e.target.value)} required/>
        </label>
      </div>
      <fieldset className="agent-tools-fieldset">
        <legend>{t('admin.agentToolsList')}</legend>
        <div className="agent-tools-grid">
          {(data.available_tools || []).map(tool => <label key={tool} className="check">
            <input type="checkbox" checked={enabledTools.includes(tool)} disabled={!toolsEnabled} onChange={() => toggleTool(tool)}/>
            <span><code>{tool}</code> — {t(`agent.tool.${tool}`)}</span>
          </label>)}
        </div>
      </fieldset>
      <label>{t('admin.agentPrompt')}
        <textarea rows={4} value={systemPrompt} onChange={e => setSystemPrompt(e.target.value)} maxLength={4000}/>
      </label>
      <div className="row">
        <button type="submit" className="primary" disabled={saving}>{saving ? t('saving') : t('admin.agentSave')}</button>
        <button type="button" disabled={saving} onClick={() => setSystemPrompt(data.default_system_prompt)}>{t('admin.agentResetPrompt')}</button>
      </div>
    </form>
    {message && <p className="success-text" role="status">{message}</p>}
    {error && <p className="error-text" role="alert">{error}</p>}
  </>}</AdminPanel>;
}
