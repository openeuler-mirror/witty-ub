/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * witty-ub is licensed under the Mulan PSL v2.
 * You can use this software according to the terms and conditions of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *     http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
 * PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

#define MODULE_NAME "LOG"

#include "log_reader.h"

#include <spawn.h>
#include <sys/wait.h>
#include <unistd.h>
#include <algorithm>
#include <cctype>
#include <cerrno>
#include <cstring>
#include <filesystem>

#include "logger.h"

namespace failure::log {
static constexpr int VEC_SCALER = 2;
using Command = std::vector<std::string>;

std::string TrimCopy(const std::string &str)
{
    std::size_t begin = 0;
    while (begin < str.size() && std::isspace(static_cast<unsigned char>(str[begin])) != 0) {
        ++begin;
    }

    std::size_t end = str.size();
    while (end > begin && std::isspace(static_cast<unsigned char>(str[end - 1])) != 0) {
        --end;
    }
    return str.substr(begin, end - begin);
}

bool HasKeywordChar(const std::string &str)
{
    return std::any_of(str.begin(), str.end(), [](unsigned char ch) { return std::isalnum(ch) != 0 || ch == '_'; });
}

std::vector<std::string> ExtractManifestKeywords(const std::string &manifest)
{
    std::vector<std::string> keywords;
    auto addKeyword = [&keywords](const std::string &candidate) {
        std::string trimmed = TrimCopy(candidate);
        if (trimmed.empty() || !HasKeywordChar(trimmed)) {
            return;
        }
        if (std::find(keywords.begin(), keywords.end(), trimmed) == keywords.end()) {
            keywords.push_back(std::move(trimmed));
        }
    };

    std::size_t pos = 0;
    while (pos < manifest.size()) {
        std::size_t start = manifest.find('<', pos);
        std::string literal = manifest.substr(pos, start == std::string::npos ? std::string::npos : start - pos);

        std::size_t partStart = 0;
        while (partStart <= literal.size()) {
            std::size_t partEnd = literal.find('|', partStart);
            size_t partEndPos = partEnd == std::string::npos ? std::string::npos : partEnd - partStart;
            addKeyword(literal.substr(partStart, partEndPos));
            if (partEnd == std::string::npos) {
                break;
            }
            partStart = partEnd + 1;
        }

        if (start == std::string::npos) {
            break;
        }
        std::size_t end = manifest.find('>', start + 1);
        if (end == std::string::npos) {
            break;
        }
        pos = end + 1;
    }
    return keywords;
}

Command BuildKeywordFilter(const std::vector<std::string> &keywords)
{
    Command command = {"grep", "-F"};
    for (const std::string &keyword : keywords) {
        command.emplace_back("-e");
        command.push_back(keyword);
    }
    return command;
}

void WaitForChildren(std::vector<pid_t> &childPids)
{
    for (pid_t pid : childPids) {
        pid_t waited = waitpid(pid, nullptr, 0);
        while (waited == -1 && errno == EINTR) {
            waited = waitpid(pid, nullptr, 0);
        }
    }
    childPids.clear();
}

FILE *SpawnPipeline(std::vector<Command> &commands, std::vector<pid_t> &childPids)
{
    int inputFd = -1;
    for (Command &command : commands) {
        int outputFds[2];
        if (pipe(outputFds) != 0) {
            if (inputFd != -1) {
                close(inputFd);
            }
            WaitForChildren(childPids);
            return nullptr;
        }
        posix_spawn_file_actions_t actions;
        posix_spawn_file_actions_init(&actions);
        if (inputFd != -1) {
            posix_spawn_file_actions_adddup2(&actions, inputFd, STDIN_FILENO);
            posix_spawn_file_actions_addclose(&actions, inputFd);
        }
        posix_spawn_file_actions_adddup2(&actions, outputFds[1], STDOUT_FILENO);
        posix_spawn_file_actions_addclose(&actions, outputFds[0]);
        posix_spawn_file_actions_addclose(&actions, outputFds[1]);
        std::vector<char *> argv;
        argv.reserve(command.size() + 1);
        for (std::string &argument : command) {
            argv.push_back(argument.data());
        }
        argv.push_back(nullptr);
        pid_t pid;
        int result = posix_spawnp(&pid, argv[0], &actions, nullptr, argv.data(), environ);
        posix_spawn_file_actions_destroy(&actions);
        close(outputFds[1]);
        if (inputFd != -1) {
            close(inputFd);
        }
        if (result != 0) {
            LOG_ERROR << "failed to spawn " << command.front() << ": " << std::strerror(result);
            close(outputFds[0]);
            WaitForChildren(childPids);
            return nullptr;
        }
        childPids.push_back(pid);
        inputFd = outputFds[0];
    }
    FILE *stream = fdopen(inputFd, "r");
    if (stream == nullptr) {
        close(inputFd);
        WaitForChildren(childPids);
    }
    return stream;
}

LogReader::LogReader(DataSourceOption option, const PathCell &pathCell, int64_t startTime, int64_t endTime)
    : option_(option),
      pathCell_(pathCell),
      startTime_(startTime),
      endTime_(endTime),
      handle_(nullptr),
      parser_(std::make_unique<LogParser>())
{
}

LogReader::~LogReader()
{
    DestroyHandle();
}

void LogReader::CreateHandle()
{
    if (!opener_ || !closer_) {
        ConfigureHandle(option_);
    }
    if (!handle_ && opener_) {
        handle_ = opener_(pathCell_.path);
    }
}

void LogReader::DestroyHandle()
{
    if (handle_ && closer_) {
        closer_(handle_);
        handle_ = nullptr;
    }
}

void LogReader::AddFailureMode(const FailureMode &mode)
{
    parser_->AddFailureMode(mode);
    for (const std::string &keyword : ExtractManifestKeywords(mode.manifest)) {
        if (std::find(keywords_.begin(), keywords_.end(), keyword) == keywords_.end()) {
            keywords_.push_back(keyword);
        }
    }
}

std::string LogReader::CollectContinuationLines(const LogTemplate &tmpl, const std::string &identifier,
                                                std::string lines)
{
    while (auto nextLine = ReadNextLine()) {
        auto nextAttributes = tmpl.Match(*nextLine);
        if (!nextAttributes || nextAttributes->find("identifier") == nextAttributes->end() ||
            nextAttributes->at("identifier") != identifier) {
            cachedLine_ = std::move(nextLine);
            break;
        }
        if (lines.capacity() < lines.size() + nextLine->size()) {
            lines.reserve((lines.size() + nextLine->size()) * VEC_SCALER);
        }
        lines.append(*nextLine);
    }
    return lines;
}

std::optional<FailureEvent> LogReader::ReadOnce()
{
    while (auto line = ReadNextLine()) {
        if (auto entry = parser_->MatchSingleLineTemplate(*line)) {
            const LogTemplate &tmpl = *entry->first;
            std::unordered_map<std::string, std::string> &attributes = entry->second;
            if (auto event = tmpl.CreateEvent(std::move(attributes), std::move(*line))) {
                event->pathCell = pathCell_;
                return event;
            }
        } else if (auto entry = parser_->MatchMultiLineTemplate(*line)) {
            const LogTemplate *tmpl = entry->first;
            std::unordered_map<std::string, std::string> &attributes = entry->second;
            auto it = attributes.find("identifier");
            std::string identifier = it->second;
            std::string lines(*line);
            lines.reserve(line->size() + readBufSize_);
            lines = CollectContinuationLines(*tmpl, identifier, std::move(lines));
            attributes.erase(it);
            if (auto event = tmpl->CreateEvent(std::move(attributes), std::move(lines))) {
                event->pathCell = pathCell_;
                return event;
            }
        }
    }

    return std::nullopt;
}

std::optional<std::string> LogReader::ReadNextLine()
{
    if (cachedLine_) {
        auto line = std::move(*cachedLine_);
        cachedLine_.reset();
        return line;
    }

    lineBuffer_.clear();
    while (fgets(readBuffer_.data(), readBuffer_.size(), handle_) != nullptr) {
        const std::size_t chunkLen = std::strlen(readBuffer_.data());
        lineBuffer_.append(readBuffer_.data(), chunkLen);

        if (chunkLen > 0 && readBuffer_[chunkLen - 1] == '\n') {
            return std::move(lineBuffer_);
        }
    }
    if (lineBuffer_.empty()) {
        return std::nullopt;
    }

    return std::move(lineBuffer_);
}

FILE *LogReader::OpenKernelLog(const std::string &path)
{
    std::string script = R"(
        BEGIN {
            mon["Jan"]=1; mon["Feb"]=2; mon["Mar"]=3; mon["Apr"]=4;
            mon["May"]=5; mon["Jun"]=6; mon["Jul"]=7; mon["Aug"]=8;
            mon["Sep"]=9; mon["Oct"]=10; mon["Nov"]=11; mon["Dec"]=12;
        }
        {
            if (index($1, "[") != 1) next;
            year = $5; sub(/\]/, "", year);
            split($4, t, ":");
            ts = mktime(year " " mon[$2] " " $3 " " t[1] " " t[2] " " t[3]);
            if (ts < s) next;
            if (ts > e) exit;
            print $0;
        }
    )";
    Command gawk = {"gawk",
                    "-v",
                    "s=" + std::to_string(startTime_ / 1000000),
                    "-v",
                    "e=" + std::to_string(endTime_ / 1000000),
                    "-e",
                    std::move(script)};
    std::vector<Command> commands;
    if (std::filesystem::is_regular_file(path)) {
        gawk.push_back(path);
    } else {
        commands.push_back({path, "-T"});
    }
    commands.push_back(std::move(gawk));
    if (!keywords_.empty()) {
        commands.push_back(BuildKeywordFilter(keywords_));
    }
    return SpawnPipeline(commands, childPids_);
}

FILE *LogReader::OpenUserLog(const std::string &path)
{
    auto startTimeStr = failure::TimestampToDatetimeStr(startTime_, "iso8601");
    auto endTimeStr = failure::TimestampToDatetimeStr(endTime_, "iso8601");
    std::string script = "$1 >= \"" + *startTimeStr + ".000000+08:00\" && $1 <= \"" + *endTimeStr + ".999999+08:00\"";
    std::vector<Command> commands = {{"awk", "-F|", std::move(script), path}};
    if (!keywords_.empty()) {
        commands.push_back(BuildKeywordFilter(keywords_));
    }
    return SpawnPipeline(commands, childPids_);
}

void LogReader::CloseLog(FILE *stream)
{
    if (fclose(stream) != 0) {
        LOG_ERROR << "failed to close log stream: " << std::strerror(errno);
    }
    WaitForChildren(childPids_);
}

void LogReader::ConfigureHandle(DataSourceOption option)
{
    if (option == DataSourceOption::KERNEL) {
        opener_ = [this](const std::string &path) {
            return OpenKernelLog(path);
        };
    } else {
        opener_ = [this](const std::string &path) {
            return OpenUserLog(path);
        };
    }
    closer_ = [this](FILE *stream) {
        CloseLog(stream);
    };
}
} // namespace failure::log
