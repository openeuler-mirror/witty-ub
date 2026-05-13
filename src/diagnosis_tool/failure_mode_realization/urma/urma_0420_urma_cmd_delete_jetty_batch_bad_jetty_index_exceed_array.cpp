#include "urma_0420_urma_cmd_delete_jetty_batch_bad_jetty_index_exceed_array.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0420UrmaCmdDeleteJettyBatchBadJettyIndexExceedArray> g_urma("urma_0420");

bool Urma0420UrmaCmdDeleteJettyBatchBadJettyIndexExceedArray::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"bad jetty index exceed array length, bad_jetty_index: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0420UrmaCmdDeleteJettyBatchBadJettyIndexExceedArray::GetName() const
{
    return "urma_cmd_delete_jetty_batch bad jetty index exceed array length,";
}

std::string Urma0420UrmaCmdDeleteJettyBatchBadJettyIndexExceedArray::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `arg.out.bad_jetty_index >= jetty_num`；该路径返回 ret";
}

RootCause Urma0420UrmaCmdDeleteJettyBatchBadJettyIndexExceedArray::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0420UrmaCmdDeleteJettyBatchBadJettyIndexExceedArray::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0420UrmaCmdDeleteJettyBatchBadJettyIndexExceedArray::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：bad jetty index exceed array length, bad_jetty_index: %.";
}

std::string Urma0420UrmaCmdDeleteJettyBatchBadJettyIndexExceedArray::GetId() const
{
    return "urma_0420";
}
} // namespace diag
