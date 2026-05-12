#include "urma_0762_urma_free_jfc_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0762UrmaFreeJfcInvalidParam> g_urma("urma_0762");

bool Urma0762UrmaFreeJfcInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0762UrmaFreeJfcInvalidParam::GetName() const
{
    return "urma_free_jfc 参数非法";
}

std::string Urma0762UrmaFreeJfcInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfc == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0762UrmaFreeJfcInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0762UrmaFreeJfcInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0762UrmaFreeJfcInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0762UrmaFreeJfcInvalidParam::GetId() const
{
    return "urma_0762";
}
} // namespace diag
