require 'sinatra'
require 'httparty'

set :bind, '0.0.0.0'
set :port, 4567

RESULTS_API = ENV.fetch('RESULTS_API_URL', 'http://localhost:8004')

get '/' do
  "AB Experiments Dashboard — connect to Results API at #{RESULTS_API}"
end

get '/experiments/:id' do
  id = params[:id]
  res = HTTParty.get("#{RESULTS_API}/v1/experiments/#{id}/summary")
  content_type :json
  res.body
end


