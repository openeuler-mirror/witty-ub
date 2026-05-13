#include "urma_0445_urma_cmd_delete_jfr_batch_bad_jfr_index_exceed_array.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0445UrmaCmdDeleteJfrBatchBadJfrIndexExceedArray> g_urma("urma_0445");

bool Urma0445UrmaCmdDeleteJfrBatchBadJfrIndexExceedArray::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"bad jfr index exceed array length, bad_jfr_index: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0445UrmaCmdDeleteJfrBatchBadJfrIndexExceedArray::GetName() const
{
    return "urma_cmd_delete_jfr_batch bad jfr index exceed array length, b";
}

std::string Urma0445UrmaCmdDeleteJfrBatchBadJfrIndexExceedArray::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `arg.out.bad_jfr_index >= jfr_num`；该路径返回 ret";
}

RootCause Urma0445UrmaCmdDeleteJfrBatchBadJfrIndexExceedArray::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0445UrmaCmdDeleteJfrBatchBadJfrIndexExceedArray::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0445UrmaCmdDeleteJfrBatchBadJfrIndexExceedArray::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：bad jfr index exceed array length, bad_jfr_index: %.";
}

std::string Urma0445UrmaCmdDeleteJfrBatchBadJfrIndexExceedArray::GetId() const
{
    return "urma_0445";
}
} // namespace diag
