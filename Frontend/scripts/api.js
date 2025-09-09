class VideoAPI{
    constructor(baseURL = 'http://127.0.0.1:8000/'){
        this.baseURL = baseURL;
    }

    async request(endpoint, options = {}){
        try{
            const url = `${this.baseURL}${endpoint}`;
            const response = await fetch(url, options);

            if(!response.ok){
                switch (response.status){
                    case 400:
                        throw new Error('Bad Request - Invalid data provided');
                    case 401:
                        throw new Error('Unauthorized - Authentication Required');
                    case 404:
                        throw new Error('Not Found - Resource does not exist');
                    case 500:
                        throw new Error('Internal Server Error');
                    default:
                        throw new Error(`HTTP ${response.status}`);
                }
            }

            return response;
        }
        catch (error){
            console.error('API Error:', error.message);
            throw error;
        }
    }

    async uploadVideo(videoFile, subtitleFormData){
        subtitleFormData.append('video', videoFile);

        const response = await this.request('api/v1/jobs/upload', {
            method: 'POST',
            body: subtitleFormData
        });

        return response.json();
    }

    async getJobStatus(jobId){
        const response = await this.request(`api/v1/jobs/${jobId}/status`);
        return response.json();
    }

    //temp work around for no redirect
    async headDownloadVideo(jobId){
        const response = await this.request(`api/v1/jobs/${jobId}/download`, { method: 'HEAD' });
        return response;
    }
}