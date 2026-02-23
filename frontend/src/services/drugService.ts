interface SearchStartRequest {
    inn_en: string;
    inn_ru: string;
    dosage: string;
    form: string;
    excipients?: string[];        // Добавлено: вспомогательные вещества
    excipient_match?: number;     // Добавлено: важность совпадения (0–100)
}

interface SearchStartResponse {
    project_id: string;
    status: string;
    message: string;
}

interface ProjectStatusResponse {
    project_id: string;
    status: 'PENDING' | 'COMPLETED' | 'FAILED';
    result?: {
        drugName: string;
        parameters: {
            cmax: number;
            auc: number;
            t_half: number;
            cv_intra: number;
        };
        articles: Array<{
            id: string;
            authors: string;
            journal: string;
            params: string[];
            dataString: string;
        }>;
    };
}

// Моковый "бэкенд"
let mockProjectId: string | null = null;
let mockStatus: ProjectStatusResponse['status'] = 'PENDING';

export const searchService = {
    async startSearch(data: SearchStartRequest): Promise<SearchStartResponse> {
        // Генерируем project_id
        mockProjectId = 'proj_' + Math.random().toString(36).substr(2, 9);
        mockStatus = 'PENDING';

        // Эмулируем асинхронную обработку
        setTimeout(() => {
            mockStatus = 'COMPLETED';
        }, 5000);

        return {
            project_id: mockProjectId,
            status: 'accepted',
            message: 'Search started',
        };
    },

    async getProjectStatus(projectId: string): Promise<ProjectStatusResponse> {
        if (!mockProjectId || projectId !== mockProjectId) {
            throw new Error('Project not found');
        }

        if (mockStatus === 'COMPLETED') {
            return {
                project_id: projectId,
                status: 'COMPLETED',
                result: {
                    drugName: 'Ибупрофен',
                    parameters: {
                        cmax: 44.9,
                        auc: 120.5,
                        t_half: 2.1,
                        cv_intra: 25,
                    },
                    articles: [
                        { id: '1', authors: 'Smith J. et al., 2018', journal: 'Int J Clin Pharmacol Ther.', params: ['Cmax', 'AUC', 'CVintra'], dataString: 'Cmax 44.9 · AUC 120.5 · CV 24%' },
                        { id: '2', authors: 'Davies N.M., 1998', journal: 'Clin Pharmacokinet.', params: ['Cmax', 'T1/2'], dataString: 'Cmax 43.8 · T½ 2.0' },
                        { id: '3', authors: 'Hinz B. et al., 2020', journal: 'Br J Clin Pharmacol.', params: ['AUC', 'T1/2', 'CVintra'], dataString: 'AUC 118.2 · T½ 2.3 · CV 26%' },
                        { id: '4', authors: 'Vree T.B. et al., 1993', journal: 'J Chromatogr B.', params: ['Cmax', 'AUC'], dataString: 'Cmax 46.2 · AUC 122.1' },
                        { id: '5', authors: 'Gonzalez I. et al., 2015', journal: 'Eur J Pharm Sci.', params: ['CVintra', 'T1/2'], dataString: 'CV 23% · T½ 1.9' },
                        { id: '6', authors: 'Rainsford K.D., 2009', journal: 'Inflammopharmacology.', params: ['Cmax', 'AUC', 'CVintra'], dataString: 'Cmax 45.1 · AUC 119.8 · CV 25%' },
                    ],
                },
            };
        }

        return {
            project_id: projectId,
            status: mockStatus,
        };
    },
};