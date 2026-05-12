#include "urma_0960_urma_get_smac_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0960UrmaGetSmacInvalidParam> g_urma("urma_0960");

bool Urma0960UrmaGetSmacInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0960UrmaGetSmacInvalidParam::GetName() const
{
    return "urma_get_smac 参数非法";
}

std::string Urma0960UrmaGetSmacInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || mac == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0960UrmaGetSmacInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0960UrmaGetSmacInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0960UrmaGetSmacInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0960UrmaGetSmacInvalidParam::GetId() const
{
    return "urma_0960";
}
} // namespace diag
