import React, { useEffect, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { ChevronDown, Download, FileText } from 'lucide-react';
import { searchStore } from '../stores/drugStore';

type Parameter = 'Cmax' | 'AUC' | 'T1/2' | 'CVintra';

// --- Редактируемые компоненты ---
function EditableParamTile({
                             title,
                             value,
                             unit,
                             selected,
                             onChange,
                             onClick,
                           }: {
  title: string;
  value: string | number;
  unit: string;
  selected: boolean;
  onChange: (val: string) => void;
  onClick: () => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [localValue, setLocalValue] = useState<string>(String(value));

  useEffect(() => {
    setLocalValue(String(value));
  }, [value]);

  const handleSave = () => {
    onChange(localValue);
    setIsEditing(false);
  };

  return (
      <div
          onClick={onClick}
          className={`bg-white rounded-2xl p-5 cursor-pointer transition-all duration-200 ${
              selected
                  ? 'border-2 border-brand-blue shadow-md bg-blue-50/30'
                  : 'border border-slate-200 shadow-sm hover:border-brand-blue/50 hover:shadow-md'
          }`}
      >
        <div className="text-slate-500 text-xs font-bold mb-2 uppercase tracking-wider">{title}</div>
        <div className="flex items-baseline gap-1">
          {isEditing ? (
              <input
                  type="text"
                  value={localValue}
                  onChange={(e) => setLocalValue(e.target.value)}
                  onBlur={handleSave}
                  onKeyDown={(e) => e.key === 'Enter' && handleSave()}
                  autoFocus
                  className="text-3xl font-bold text-slate-900 w-20 outline-none border-b-2 border-brand-blue"
              />
          ) : (
              <span
                  className="text-3xl font-bold text-slate-900 hover:text-brand-blue transition-colors"
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsEditing(true);
                  }}
              >
            {localValue}
          </span>
          )}
          <span className="text-sm text-slate-500">{unit}</span>
        </div>
      </div>
  );
}

function EditableCalcTile({
                            title,
                            value,
                            unit,
                            onChange,
                          }: {
  title: string;
  value: string | number;
  unit: string;
  onChange: (val: number) => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [localValue, setLocalValue] = useState<string>(String(value));

  useEffect(() => {
    setLocalValue(String(value));
  }, [value]);

  const handleSave = () => {
    const num = parseFloat(localValue);
    if (!isNaN(num)) {
      onChange(num);
    }
    setIsEditing(false);
  };

  return (
      <div className="bg-slate-50 rounded-2xl p-4 border border-slate-100 flex flex-col items-center justify-center text-center">
        <div className="text-slate-500 text-[10px] font-bold mb-2 uppercase tracking-wider leading-tight h-8 flex items-center justify-center">
          {title}
        </div>
        <div className="flex items-baseline gap-1">
          {isEditing ? (
              <input
                  type="number"
                  step="any"
                  value={localValue}
                  onChange={(e) => setLocalValue(e.target.value)}
                  onBlur={handleSave}
                  onKeyDown={(e) => e.key === 'Enter' && handleSave()}
                  autoFocus
                  className="text-4xl font-bold text-slate-900 w-20 outline-none border-b-2 border-brand-blue"
              />
          ) : (
              <span
                  className="text-4xl font-bold text-slate-900 hover:text-brand-blue transition-colors"
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsEditing(true);
                  }}
              >
            {localValue}
          </span>
          )}
          {unit && <span className="text-lg text-slate-500 font-medium">{unit}</span>}
        </div>
      </div>
  );
}

export default observer(function ResultsPage({ onBack }: { onBack: () => void }) {
  const [selectedParams, setSelectedParams] = useState<Parameter[]>([]);
  const [dropoutRate, setDropoutRate] = useState(20);
  const [screenFail, setScreenFail] = useState(12);

  // Локальные состояния для редактируемых параметров
  const [cmax, setCmax] = useState<number | null>(searchStore.parameters.cmax);
  const [auc, setAuc] = useState<number | null>(searchStore.parameters.auc);
  const [tHalf, setTHalf] = useState<number | null>(searchStore.parameters.t_half);
  const [cvIntra, setCvIntra] = useState<number>(searchStore.parameters.cv_intra || 25);

  const [delta, setDelta] = useState<number>(20); // Ожидаемая разница
  const [power, setPower] = useState<number>(80); // Мощность
  const [alpha, setAlpha] = useState<number>(0.05); // Уровень значимости

  // Синхронизация с стором при изменении
  useEffect(() => {
    setCmax(searchStore.parameters.cmax);
    setAuc(searchStore.parameters.auc);
    setTHalf(searchStore.parameters.t_half);
    setCvIntra(searchStore.parameters.cv_intra || 25);
  }, [
    searchStore.parameters.cmax,
    searchStore.parameters.auc,
    searchStore.parameters.t_half,
    searchStore.parameters.cv_intra,
  ]);

  const toggleParam = (param: Parameter) => {
    setSelectedParams((prev) =>
        prev.includes(param) ? prev.filter((p) => p !== param) : [...prev, param]
    );
  };

  const isArticleVisible = (article: any) => {
    if (selectedParams.length === 0) return true;
    return selectedParams.every((param) => article.params.includes(param));
  };

  // Base calculation logic
  const baseVolume = 30; // Можно вычислять по формуле позже
  const withDropout = Math.ceil(baseVolume / (1 - dropoutRate / 100));
  const withScreenFail = Math.ceil(withDropout / (1 - screenFail / 100));

  // Ждём завершения поиска
  if (searchStore.status === 'idle' || searchStore.status === 'searching') {
    return (
        <div className="text-center py-20">
          <p className="text-xl text-slate-600">Ожидание результатов...</p>
        </div>
    );
  }

  if (searchStore.status === 'failed') {
    return (
        <div className="text-center py-20">
          <p className="text-xl text-red-600">Ошибка загрузки данных.</p>
        </div>
    );
  }

  return (
      <div className="animate-in fade-in duration-500">
        <div className="mb-8">
          <button onClick={onBack} className="text-brand-blue hover:underline mb-4 text-sm font-medium">
            &larr; Назад к поиску
          </button>
          <div className="flex items-center gap-4">
            <h1 className="text-4xl font-serif text-brand-blue">
              Результаты поиска: {searchStore.drugName}
            </h1>
            <span className="bg-blue-100 text-brand-blue text-xs font-bold px-2 py-1 rounded uppercase tracking-wider">
            Готово
          </span>
          </div>
          <p className="text-slate-500 mt-2">
            Агрегированные данные из {searchStore.articles.length} источников · Обновлено сегодня
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* LEFT COLUMN */}
          <div className="flex flex-col gap-8">
            <section>
              <h2 className="text-brand-blue font-medium text-lg mb-4">Фармакокинетические параметры</h2>
              <div className="grid grid-cols-2 gap-4">
                <EditableParamTile
                    title="C MAX"
                    value={cmax?.toFixed(1) || '-'}
                    unit="нг/мл"
                    selected={selectedParams.includes('Cmax')}
                    onChange={(val) => {
                      const parsed = parseFloat(val);
                      setCmax(isNaN(parsed) ? null : parsed);
                      searchStore.setParam('cmax', isNaN(parsed) ? null : parsed); // Сохраняем в стор
                    }}
                    onClick={() => toggleParam('Cmax')}
                />
                <EditableParamTile
                    title="AUC"
                    value={auc?.toFixed(1) || '-'}
                    unit="нг·ч/мл"
                    selected={selectedParams.includes('AUC')}
                    onChange={(val) => {
                      const parsed = parseFloat(val);
                      setAuc(isNaN(parsed) ? null : parsed);
                      searchStore.setParam('auc', isNaN(parsed) ? null : parsed);
                    }}
                    onClick={() => toggleParam('AUC')}
                />
                <EditableParamTile
                    title="T½"
                    value={tHalf?.toFixed(1) || '-'}
                    unit="часов"
                    selected={selectedParams.includes('T1/2')}
                    onChange={(val) => {
                      const parsed = parseFloat(val);
                      setTHalf(isNaN(parsed) ? null : parsed);
                      searchStore.setParam('t_half', isNaN(parsed) ? null : parsed);
                    }}
                    onClick={() => toggleParam('T1/2')}
                />
                <EditableParamTile
                    title="CV INTRA"
                    value={`${cvIntra}`}
                    unit="%"
                    selected={selectedParams.includes('CVintra')}
                    onChange={(val) => {
                      const parsed = parseFloat(val);
                      const value = isNaN(parsed) ? 25 : parsed;
                      setCvIntra(value);
                      searchStore.setParam('cv_intra', value);
                    }}
                    onClick={() => toggleParam('CVintra')}
                />
              </div>
              <p className="text-slate-500 text-xs mt-3 text-center">
                Нажмите на параметр, чтобы отфильтровать источники
              </p>
            </section>

            {/* Дополнительные параметры препарата */}
            <section>
              <h2 className="text-brand-blue font-medium text-lg mb-4">Дополнительные параметры препарата</h2>
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
                <div className="flex justify-between py-3 border-b border-slate-100">
                  <span className="text-slate-600">Биодоступность</span>
                  <span className="font-medium text-slate-900">85–95%</span>
                </div>
                <div className="flex justify-between py-3 border-b border-slate-100">
                  <span className="text-slate-600">Связь с белками</span>
                  <span className="font-medium text-slate-900">99%</span>
                </div>
                <div className="flex justify-between py-3 border-b border-slate-100">
                  <span className="text-slate-600">Метаболиты</span>
                  <span className="font-medium text-slate-900">активные</span>
                </div>
                <div className="flex justify-between py-3">
                  <span className="text-slate-600">Период полувыведения</span>
                  <span className="font-medium text-slate-900">2–4 ч</span>
                </div>
              </div>
            </section>
          </div>

          {/* CENTRAL COLUMN */}
          <div className="flex flex-col gap-8">
            <section className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
              <h2 className="text-brand-blue font-serif text-xl mb-6 text-center">Калькулятор объема выборки</h2>

              <div className="grid grid-cols-2 gap-4 mb-6">
                <EditableCalcTile
                    title="ОЖИДАЕМАЯ РАЗНИЦА (Δ)"
                    value={delta}
                    unit="%"
                    onChange={(val) => setDelta(val)}
                />
                <EditableCalcTile
                    title="МОЩНОСТЬ (1-β)"
                    value={power}
                    unit="%"
                    onChange={(val) => setPower(val)}
                />
                <EditableCalcTile
                    title="УРОВЕНЬ ЗНАЧИМОСТИ (α)"
                    value={alpha}
                    unit=""
                    onChange={(val) => setAlpha(val)}
                />
                <EditableCalcTile
                    title="ВНУТРИСУБЪЕКТНЫЙ CV"
                    value={cvIntra}
                    unit="%"
                    onChange={(val) => {
                      setCvIntra(val);
                      searchStore.setParam('cv_intra', val);
                    }}
                />
              </div>

              <div className="bg-slate-50 rounded-xl p-4 mb-6 border border-slate-100">
                <div className="flex justify-between mb-2">
                  <span className="text-slate-600 text-sm">Базовый объем:</span>
                  <span className="font-bold text-slate-900">{baseVolume} чел</span>
                </div>
                <div className="flex justify-between mb-2">
                  <span className="text-slate-600 text-sm">С учетом dropout ({dropoutRate}%):</span>
                  <span className="font-bold text-slate-900">{withDropout} чел</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600 text-sm">С учетом screen fail ({screenFail}%):</span>
                  <span className="font-bold text-brand-blue">{withScreenFail} чел</span>
                </div>
              </div>

              <div className="space-y-6">
                <div>
                  <div className="flex justify-between text-sm font-medium text-brand-blue mb-2 uppercase tracking-wider">
                    <span>Dropout rate</span>
                    <span>{dropoutRate}%</span>
                  </div>
                  <input
                      type="range"
                      min="0"
                      max="50"
                      value={dropoutRate}
                      onChange={(e) => setDropoutRate(Number(e.target.value))}
                      className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand-blue"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-sm font-medium text-brand-blue mb-2 uppercase tracking-wider">
                    <span>Screen fail</span>
                    <span>{screenFail}%</span>
                  </div>
                  <input
                      type="range"
                      min="0"
                      max="50"
                      value={screenFail}
                      onChange={(e) => setScreenFail(Number(e.target.value))}
                      className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand-blue"
                  />
                </div>
              </div>
            </section>

            {/* Рекомендуемый дизайн */}
            <section>
              <h2 className="text-brand-blue font-medium text-lg mb-4">Рекомендуемый дизайн</h2>
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
                <h3 className="text-2xl font-serif text-brand-blue mb-3">2×2 кроссовер</h3>
                <p className="text-slate-600 text-sm leading-relaxed mb-4">
                  Низкая вариабельность (CV &lt; 30%) позволяет использовать классический двухпериодный кроссовер.
                  Рекомендован EMA Guideline on the Investigation of Bioequivalence (2010).
                </p>
                <button className="text-brand-blue font-medium text-sm hover:underline flex items-center gap-1">
                  Подробнее о дизайне &rarr;
                </button>
              </div>
            </section>

            {/* Схема рандомизации */}
            <section>
              <h2 className="text-brand-blue font-medium text-lg mb-4">Схема рандомизации</h2>
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
                <div className="border border-dashed border-slate-300 rounded-xl p-4 text-center mb-4 bg-slate-50">
                <span className="text-slate-600 text-sm">
                  Последовательность: <strong className="text-slate-900">A/B · B/A</strong>
                </span>
                </div>
                <div className="flex gap-3">
                  <button className="flex-1 py-2.5 border-2 border-brand-blue text-brand-blue rounded-lg font-medium hover:bg-blue-50 transition-colors text-sm">
                    Сгенерировать схему
                  </button>
                  <button className="flex-1 py-2.5 bg-brand-green text-white rounded-lg font-medium hover:bg-emerald-600 transition-colors flex items-center justify-center gap-2 text-sm">
                    <Download size={16} /> Скачать
                  </button>
                </div>
              </div>
            </section>
          </div>

          {/* RIGHT COLUMN */}
          <div className="flex flex-col h-full">
            <div className="flex justify-between items-end mb-4">
              <h2 className="text-brand-blue font-medium text-lg">Все источники</h2>
              <span className="bg-slate-200 text-slate-600 text-xs font-bold px-2 py-1 rounded-full">
              {searchStore.articles.length} статей
            </span>
            </div>

            <div className="flex-1 flex flex-col gap-3 mb-6 overflow-y-auto pr-2" style={{ maxHeight: '800px' }}>
              {searchStore.articles.map((article) => {
                const visible = isArticleVisible(article);
                return (
                    <div
                        key={article.id}
                        className={`bg-white rounded-xl p-4 border transition-all duration-300 cursor-pointer hover:shadow-md ${
                            visible
                                ? selectedParams.length > 0
                                    ? 'border-blue-200 shadow-sm'
                                    : 'border-slate-200 shadow-sm'
                                : 'opacity-40 border-slate-100 grayscale-[50%]'
                        }`}
                    >
                      <div className="flex justify-between items-start mb-1">
                        <h4 className="font-bold text-slate-900">{article.authors}</h4>
                        <ChevronDown size={16} className="text-slate-400" />
                      </div>
                      <p className="text-slate-500 text-sm italic mb-3">{article.journal}</p>
                      <div className="flex flex-wrap gap-2">
                        {article.params.map((p) => (
                            <span
                                key={p}
                                className={`text-xs px-2 py-1 rounded border ${
                                    selectedParams.includes(p)
                                        ? 'bg-blue-50 border-blue-200 text-brand-blue font-medium'
                                        : 'bg-slate-50 border-slate-200 text-slate-600'
                                }`}
                            >
                        {p}
                      </span>
                        ))}
                      </div>
                      <p className="text-xs text-slate-600 mt-3 pt-3 border-t border-slate-100">
                        {article.dataString}
                      </p>
                    </div>
                );
              })}
            </div>

            <div className="mt-auto pt-4">
              <p className="text-slate-500 text-xs text-right mb-2">
                На основе данных из {searchStore.articles.length} источников
              </p>
              <button className="w-full h-16 bg-brand-blue hover:bg-[#153E75] text-white rounded-2xl font-bold text-lg tracking-wide shadow-[0_4px_10px_rgba(30,58,138,0.2)] transition-all flex items-center justify-center gap-3 uppercase">
                <FileText size={24} />
                Сгенерировать синопсис
              </button>
            </div>
          </div>
        </div>
      </div>
  );
});