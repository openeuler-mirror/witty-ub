#include "urma_failure_660.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure660> g_urma("urma_660");

bool UrmaFailure660::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_jfs' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'jfs still actived, please deactived first'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure660::GetName() const
{
    return "释放JFS过程中依赖步骤失败";
}

std::string UrmaFailure660::GetRootCauseDesc() const
{
    return "函数用于释放JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure660::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure660::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure660::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jfs，jfs still actived, please deactived first。";
}

std::string UrmaFailure660::GetId() const
{
    return "urma_660";
}

} // namespace diag
