FROM ruby:3.2-alpine

WORKDIR /app

RUN apk add --no-cache build-base

COPY Gemfile Gemfile.lock ./
RUN bundle install

COPY app.rb ./

EXPOSE 4567
CMD ["ruby", "app.rb"]


