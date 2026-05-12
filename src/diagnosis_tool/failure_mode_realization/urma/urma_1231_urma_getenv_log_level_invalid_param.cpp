#include "urma_1231_urma_getenv_log_level_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1231UrmaGetenvLogLevelInvalidParam> g_urma("urma_1231");

bool Urma1231UrmaGetenvLogLevelInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter: log level str."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1231UrmaGetenvLogLevelInvalidParam::GetName() const
{
    return "urma_getenv_log_level 参数非法";
}

std::string Urma1231UrmaGetenvLogLevelInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `strnlen(level_str, URMA_LOG_LEVEL_ENV_MAX_BUF_LEN) >= "
           "URMA_LOG_LEVEL_ENV_MAX_BUF_LEN`";
}

RootCause Urma1231UrmaGetenvLogLevelInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1231UrmaGetenvLogLevelInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1231UrmaGetenvLogLevelInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter: log level str.";
}

std::string Urma1231UrmaGetenvLogLevelInvalidParam::GetId() const
{
    return "urma_1231";
}
} // namespace diag
