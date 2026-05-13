#include "urma_0434_urma_cmd_delete_jfc_batch_bad_jfc_index_exceed_array.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0434UrmaCmdDeleteJfcBatchBadJfcIndexExceedArray> g_urma("urma_0434");

bool Urma0434UrmaCmdDeleteJfcBatchBadJfcIndexExceedArray::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"bad jfc index exceed array length, bad_jfc_index: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0434UrmaCmdDeleteJfcBatchBadJfcIndexExceedArray::GetName() const
{
    return "urma_cmd_delete_jfc_batch bad jfc index exceed array length, b";
}

std::string Urma0434UrmaCmdDeleteJfcBatchBadJfcIndexExceedArray::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `arg.out.bad_jfc_index >= jfc_num`；该路径返回 ret";
}

RootCause Urma0434UrmaCmdDeleteJfcBatchBadJfcIndexExceedArray::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0434UrmaCmdDeleteJfcBatchBadJfcIndexExceedArray::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0434UrmaCmdDeleteJfcBatchBadJfcIndexExceedArray::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：bad jfc index exceed array length, bad_jfc_index: %.";
}

std::string Urma0434UrmaCmdDeleteJfcBatchBadJfcIndexExceedArray::GetId() const
{
    return "urma_0434";
}
} // namespace diag
