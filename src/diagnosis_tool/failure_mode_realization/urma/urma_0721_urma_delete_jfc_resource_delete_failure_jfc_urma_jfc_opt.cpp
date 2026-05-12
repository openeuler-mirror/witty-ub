#include "urma_0721_urma_delete_jfc_resource_delete_failure_jfc_urma_jfc_opt.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0721UrmaDeleteJfcResourceDeleteFailureJfcUrmaJfcOpt> g_urma("urma_0721");

bool Urma0721UrmaDeleteJfcResourceDeleteFailureJfcUrmaJfcOpt::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jfc is deactived, can not delete."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0721UrmaDeleteJfcResourceDeleteFailureJfcUrmaJfcOpt::GetName() const
{
    return "urma_delete_jfc 删除资源失败（jfc->urma_jfc_opt.is_actived == false）";
}

std::string Urma0721UrmaDeleteJfcResourceDeleteFailureJfcUrmaJfcOpt::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0721UrmaDeleteJfcResourceDeleteFailureJfcUrmaJfcOpt::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0721UrmaDeleteJfcResourceDeleteFailureJfcUrmaJfcOpt::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0721UrmaDeleteJfcResourceDeleteFailureJfcUrmaJfcOpt::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfc is deactived, can not delete.";
}

std::string Urma0721UrmaDeleteJfcResourceDeleteFailureJfcUrmaJfcOpt::GetId() const
{
    return "urma_0721";
}
} // namespace diag
