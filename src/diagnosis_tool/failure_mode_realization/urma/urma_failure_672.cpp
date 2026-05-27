#include "urma_failure_672.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure672> g_urma("urma_672");

bool UrmaFailure672::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_jfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'jfr still actived, please deactived first'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure672::GetName() const
{
    return "释放JFR过程中依赖步骤失败";
}

std::string UrmaFailure672::GetRootCauseDesc() const
{
    return "函数用于释放JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure672::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure672::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure672::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jfr，jfr still actived, please deactived first。";
}

std::string UrmaFailure672::GetId() const
{
    return "urma_672";
}

} // namespace diag
