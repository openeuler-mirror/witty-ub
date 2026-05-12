#include "urma_0556_urma_cmd_set_tp_attr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0556UrmaCmdSetTpAttrInvalidParam> g_urma("urma_0556");

bool Urma0556UrmaCmdSetTpAttrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0556UrmaCmdSetTpAttrInvalidParam::GetName() const
{
    return "urma_cmd_set_tp_attr 参数非法";
}

std::string Urma0556UrmaCmdSetTpAttrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || tp_attr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0556UrmaCmdSetTpAttrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0556UrmaCmdSetTpAttrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0556UrmaCmdSetTpAttrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0556UrmaCmdSetTpAttrInvalidParam::GetId() const
{
    return "urma_0556";
}
} // namespace diag
