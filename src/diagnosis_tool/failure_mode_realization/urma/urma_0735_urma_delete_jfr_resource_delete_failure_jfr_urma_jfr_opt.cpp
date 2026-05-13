#include "urma_0735_urma_delete_jfr_resource_delete_failure_jfr_urma_jfr_opt.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0735UrmaDeleteJfrResourceDeleteFailureJfrUrmaJfrOpt> g_urma("urma_0735");

bool Urma0735UrmaDeleteJfrResourceDeleteFailureJfrUrmaJfrOpt::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jfr is deactived, can not delete."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0735UrmaDeleteJfrResourceDeleteFailureJfrUrmaJfrOpt::GetName() const
{
    return "urma_delete_jfr 删除资源失败（jfr->urma_jfr_opt.is_actived == false）";
}

std::string Urma0735UrmaDeleteJfrResourceDeleteFailureJfrUrmaJfrOpt::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0735UrmaDeleteJfrResourceDeleteFailureJfrUrmaJfrOpt::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0735UrmaDeleteJfrResourceDeleteFailureJfrUrmaJfrOpt::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0735UrmaDeleteJfrResourceDeleteFailureJfrUrmaJfrOpt::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfr is deactived, can not delete.";
}

std::string Urma0735UrmaDeleteJfrResourceDeleteFailureJfrUrmaJfrOpt::GetId() const
{
    return "urma_0735";
}
} // namespace diag
