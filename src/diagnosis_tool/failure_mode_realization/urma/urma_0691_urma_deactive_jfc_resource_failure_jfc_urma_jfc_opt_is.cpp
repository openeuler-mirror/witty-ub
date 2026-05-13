#include "urma_0691_urma_deactive_jfc_resource_failure_jfc_urma_jfc_opt_is.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0691UrmaDeactiveJfcResourceFailureJfcUrmaJfcOptIs> g_urma("urma_0691");

bool Urma0691UrmaDeactiveJfcResourceFailureJfcUrmaJfcOptIs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Jfc state is wrong in deactive_jfc."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0691UrmaDeactiveJfcResourceFailureJfcUrmaJfcOptIs::GetName() const
{
    return "urma_deactive_jfc 激活资源失败（jfc->urma_jfc_opt.is_actived == false）";
}

std::string Urma0691UrmaDeactiveJfcResourceFailureJfcUrmaJfcOptIs::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0691UrmaDeactiveJfcResourceFailureJfcUrmaJfcOptIs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0691UrmaDeactiveJfcResourceFailureJfcUrmaJfcOptIs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0691UrmaDeactiveJfcResourceFailureJfcUrmaJfcOptIs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Jfc state is wrong in deactive_jfc.";
}

std::string Urma0691UrmaDeactiveJfcResourceFailureJfcUrmaJfcOptIs::GetId() const
{
    return "urma_0691";
}
} // namespace diag
