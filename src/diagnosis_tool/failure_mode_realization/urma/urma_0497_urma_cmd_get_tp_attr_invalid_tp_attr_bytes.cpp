#include "urma_0497_urma_cmd_get_tp_attr_invalid_tp_attr_bytes.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0497UrmaCmdGetTpAttrInvalidTpAttrBytes> g_urma("urma_0497");

bool Urma0497UrmaCmdGetTpAttrInvalidTpAttrBytes::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid tp_attr bytes."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0497UrmaCmdGetTpAttrInvalidTpAttrBytes::GetName() const
{
    return "urma_cmd_get_tp_attr Invalid tp_attr bytes.";
}

std::string Urma0497UrmaCmdGetTpAttrInvalidTpAttrBytes::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `sizeof(urma_tp_attr_value_t) != sizeof(arg.out.tp_attr)`；该路径返回 URMA_EINVAL";
}

RootCause Urma0497UrmaCmdGetTpAttrInvalidTpAttrBytes::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0497UrmaCmdGetTpAttrInvalidTpAttrBytes::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0497UrmaCmdGetTpAttrInvalidTpAttrBytes::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid tp_attr bytes.";
}

std::string Urma0497UrmaCmdGetTpAttrInvalidTpAttrBytes::GetId() const
{
    return "urma_0497";
}
} // namespace diag
