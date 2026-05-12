#include "urma_0829_urma_set_jfc_opt_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0829UrmaSetJfcOptInvalidParam> g_urma("urma_0829");

bool Urma0829UrmaSetJfcOptInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0829UrmaSetJfcOptInvalidParam::GetName() const
{
    return "urma_set_jfc_opt 参数非法";
}

std::string Urma0829UrmaSetJfcOptInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfc == NULL || buf == NULL || opt == 0 || len == 0`；该路径返回 URMA_EINVAL";
}

RootCause Urma0829UrmaSetJfcOptInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0829UrmaSetJfcOptInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0829UrmaSetJfcOptInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0829UrmaSetJfcOptInvalidParam::GetId() const
{
    return "urma_0829";
}
} // namespace diag
