#include "urma_0873_urma_poll_jfc_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0873UrmaPollJfcInvalidParam> g_urma("urma_0873");

bool Urma0873UrmaPollJfcInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0873UrmaPollJfcInvalidParam::GetName() const
{
    return "urma_poll_jfc 参数非法";
}

std::string Urma0873UrmaPollJfcInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `dp_ops == NULL || dp_ops->poll_jfc == NULL || cr == NULL || cr_cnt < "
           "0`；该路径返回 -1";
}

RootCause Urma0873UrmaPollJfcInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0873UrmaPollJfcInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0873UrmaPollJfcInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0873UrmaPollJfcInvalidParam::GetId() const
{
    return "urma_0873";
}
} // namespace diag
