#include "urma_0619_urma_alloc_jfc_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0619UrmaAllocJfcInvalidParam> g_urma("urma_0619");

bool Urma0619UrmaAllocJfcInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0619UrmaAllocJfcInvalidParam::GetName() const
{
    return "urma_alloc_jfc 参数非法";
}

std::string Urma0619UrmaAllocJfcInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `urma_ctx == NULL || cfg == NULL || jfc == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0619UrmaAllocJfcInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0619UrmaAllocJfcInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0619UrmaAllocJfcInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0619UrmaAllocJfcInvalidParam::GetId() const
{
    return "urma_0619";
}
} // namespace diag
