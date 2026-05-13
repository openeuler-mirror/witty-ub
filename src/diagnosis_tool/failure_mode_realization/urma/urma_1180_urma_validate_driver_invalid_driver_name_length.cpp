#include "urma_1180_urma_validate_driver_invalid_driver_name_length.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1180UrmaValidateDriverInvalidDriverNameLength> g_urma("urma_1180");

bool Urma1180UrmaValidateDriverInvalidDriverNameLength::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid driver name length."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1180UrmaValidateDriverInvalidDriverNameLength::GetName() const
{
    return "urma_validate_driver Invalid driver name length.";
}

std::string Urma1180UrmaValidateDriverInvalidDriverNameLength::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `len > NAME_MAX`；该路径返回 false";
}

RootCause Urma1180UrmaValidateDriverInvalidDriverNameLength::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1180UrmaValidateDriverInvalidDriverNameLength::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1180UrmaValidateDriverInvalidDriverNameLength::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid driver name length.";
}

std::string Urma1180UrmaValidateDriverInvalidDriverNameLength::GetId() const
{
    return "urma_1180";
}
} // namespace diag
