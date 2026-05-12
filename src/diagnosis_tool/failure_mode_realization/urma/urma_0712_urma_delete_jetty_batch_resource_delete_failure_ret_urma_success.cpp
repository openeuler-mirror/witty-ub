#include "urma_0712_urma_delete_jetty_batch_resource_delete_failure_ret_urma_success.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0712UrmaDeleteJettyBatchResourceDeleteFailureRetUrmaSuccess> g_urma("urma_0712");

bool Urma0712UrmaDeleteJettyBatchResourceDeleteFailureRetUrmaSuccess::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete jetty batch, ret: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0712UrmaDeleteJettyBatchResourceDeleteFailureRetUrmaSuccess::GetName() const
{
    return "urma_delete_jetty_batch 删除资源失败（ret != URMA_SUCCESS）";
}

std::string Urma0712UrmaDeleteJettyBatchResourceDeleteFailureRetUrmaSuccess::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0712UrmaDeleteJettyBatchResourceDeleteFailureRetUrmaSuccess::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0712UrmaDeleteJettyBatchResourceDeleteFailureRetUrmaSuccess::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0712UrmaDeleteJettyBatchResourceDeleteFailureRetUrmaSuccess::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete jetty batch, ret: %.";
}

std::string Urma0712UrmaDeleteJettyBatchResourceDeleteFailureRetUrmaSuccess::GetId() const
{
    return "urma_0712";
}
} // namespace diag
