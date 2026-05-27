#include "urma_failure_013.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure013> g_urma("urma_013");

bool UrmaFailure013::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unimport_pjetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to init active indices'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure013::GetName() const
{
    return "初始化物理 Jetty过程中依赖步骤失败";
}

std::string UrmaFailure013::GetRootCauseDesc() const
{
    return "函数用于初始化物理 "
           "Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。";
}

RootCause UrmaFailure013::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure013::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure013::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_unimport_pjetty，Failed to init active indices。";
}

std::string UrmaFailure013::GetId() const
{
    return "urma_013";
}

} // namespace diag
