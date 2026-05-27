#include "urma_failure_733.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure733> g_urma("urma_733");

bool UrmaFailure733::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'update_mapping_hash_table' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'topo info doesn'\\''t have cur_node'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure733::GetName() const
{
    return "释放URMA资源过程中依赖步骤失败";
}

std::string UrmaFailure733::GetRootCauseDesc() const
{
    return "函数用于释放URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URM"
           "A操作失败。";
}

RootCause UrmaFailure733::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure733::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure733::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：update_mapping_hash_table，topo info doesn't have cur_node";
}

std::string UrmaFailure733::GetId() const
{
    return "urma_733";
}

} // namespace diag
