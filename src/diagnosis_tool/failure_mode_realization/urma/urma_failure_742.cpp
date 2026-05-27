#include "urma_failure_742.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure742> g_urma("urma_742");

bool UrmaFailure742::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'update_mapping_hash_table' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'topo info doesn'\\''t have cur_node'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure742::GetName() const
{
    return "释放URMA资源过程中依赖步骤失败";
}

std::string UrmaFailure742::GetRootCauseDesc() const
{
    return "函数用于释放URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URM"
           "A操作失败。";
}

RootCause UrmaFailure742::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure742::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure742::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：update_mapping_hash_table，topo info doesn't have cur_node。";
}

std::string UrmaFailure742::GetId() const
{
    return "urma_742";
}

} // namespace diag
