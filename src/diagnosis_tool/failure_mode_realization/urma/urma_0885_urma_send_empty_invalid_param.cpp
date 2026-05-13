#include "urma_0885_urma_send_empty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0885UrmaSendEmptyInvalidParam> g_urma("urma_0885");

bool Urma0885UrmaSendEmptyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"null pointer exists in tjfr."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0885UrmaSendEmptyInvalidParam::GetName() const
{
    return "urma_send 空指针参数非法";
}

std::string Urma0885UrmaSendEmptyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `checkout_valid_tjfr(target_jfr) != URMA_SUCCESS`；该路径返回 URMA_EINVAL";
}

RootCause Urma0885UrmaSendEmptyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0885UrmaSendEmptyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0885UrmaSendEmptyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：null pointer exists in tjfr.";
}

std::string Urma0885UrmaSendEmptyInvalidParam::GetId() const
{
    return "urma_0885";
}
} // namespace diag
