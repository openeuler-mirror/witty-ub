#include "urma_failure_709.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure709> g_urma("urma_709");

bool UrmaFailure709::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_wait_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Faile to wait jfc non-block, ret:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure709::GetName() const
{
    return "等待JFC过程中依赖步骤失败";
}

std::string UrmaFailure709::GetRootCauseDesc() const
{
    return "函数用于等待JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure709::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure709::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure709::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_wait_jfc，Faile to wait jfc non-block, ret:，, errno:。";
}

std::string UrmaFailure709::GetId() const
{
    return "urma_709";
}

} // namespace diag
