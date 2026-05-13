#include "urma_0695_urma_deactive_jfr_resource_failure_jfr_urma_jfr_opt_is.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0695UrmaDeactiveJfrResourceFailureJfrUrmaJfrOptIs> g_urma("urma_0695");

bool Urma0695UrmaDeactiveJfrResourceFailureJfrUrmaJfrOptIs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jfr state is wrong in deactive_jfr."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0695UrmaDeactiveJfrResourceFailureJfrUrmaJfrOptIs::GetName() const
{
    return "urma_deactive_jfr 激活资源失败（jfr->urma_jfr_opt.is_actived == false）";
}

std::string Urma0695UrmaDeactiveJfrResourceFailureJfrUrmaJfrOptIs::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0695UrmaDeactiveJfrResourceFailureJfrUrmaJfrOptIs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0695UrmaDeactiveJfrResourceFailureJfrUrmaJfrOptIs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0695UrmaDeactiveJfrResourceFailureJfrUrmaJfrOptIs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfr state is wrong in deactive_jfr.";
}

std::string Urma0695UrmaDeactiveJfrResourceFailureJfrUrmaJfrOptIs::GetId() const
{
    return "urma_0695";
}
} // namespace diag
