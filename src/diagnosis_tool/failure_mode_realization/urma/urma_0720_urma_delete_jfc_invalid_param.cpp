#include "urma_0720_urma_delete_jfc_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0720UrmaDeleteJfcInvalidParam> g_urma("urma_0720");

bool Urma0720UrmaDeleteJfcInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0720UrmaDeleteJfcInvalidParam::GetName() const
{
    return "urma_delete_jfc 参数非法";
}

std::string Urma0720UrmaDeleteJfcInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfc == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0720UrmaDeleteJfcInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0720UrmaDeleteJfcInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0720UrmaDeleteJfcInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0720UrmaDeleteJfcInvalidParam::GetId() const
{
    return "urma_0720";
}
} // namespace diag
