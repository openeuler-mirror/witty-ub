#include "urma_0906_urma_log_set_thread_tag_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0906UrmaLogSetThreadTagInvalidParam> g_urma("urma_0906");

bool Urma0906UrmaLogSetThreadTagInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0906UrmaLogSetThreadTagInvalidParam::GetName() const
{
    return "urma_log_set_thread_tag 参数非法";
}

std::string Urma0906UrmaLogSetThreadTagInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `tag == NULL || strnlen(tag, URMA_MAX_NAME) >= URMA_MAX_NAME`";
}

RootCause Urma0906UrmaLogSetThreadTagInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0906UrmaLogSetThreadTagInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0906UrmaLogSetThreadTagInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0906UrmaLogSetThreadTagInvalidParam::GetId() const
{
    return "urma_0906";
}
} // namespace diag
