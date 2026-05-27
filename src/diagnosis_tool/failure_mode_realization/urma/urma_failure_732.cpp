#include "urma_failure_732.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure732> g_urma("urma_732");

bool UrmaFailure732::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'update_mapping_hash_table' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to add port eid to mapping hash table'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure732::GetName() const
{
    return "执行端口过程中依赖步骤失败";
}

std::string UrmaFailure732::GetRootCauseDesc() const
{
    return "函数用于执行端口，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure732::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure732::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure732::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：update_mapping_hash_table，Failed to add port eid to mapping hash table";
}

std::string UrmaFailure732::GetId() const
{
    return "urma_732";
}

} // namespace diag
