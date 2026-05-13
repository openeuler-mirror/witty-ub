#include "urma_0908_urma_create_context_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0908UrmaCreateContextInvalidParam> g_urma("urma_0908");

bool Urma0908UrmaCreateContextInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter with err dev or ops."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0908UrmaCreateContextInvalidParam::GetName() const
{
    return "urma_create_context 参数非法";
}

std::string Urma0908UrmaCreateContextInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `dev == NULL || dev->ops == NULL || dev->ops->create_context == "
           "NULL`；该路径返回 NULL";
}

RootCause Urma0908UrmaCreateContextInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0908UrmaCreateContextInvalidParam::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string Urma0908UrmaCreateContextInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter with err dev or ops.";
}

std::string Urma0908UrmaCreateContextInvalidParam::GetId() const
{
    return "urma_0908";
}
} // namespace diag
