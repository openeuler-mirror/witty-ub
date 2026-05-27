#include "urma_failure_081.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure081> g_urma("urma_081");

bool UrmaFailure081::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_modify_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'modify pjetty fail, index:' | grep -F ', ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure081::GetName() const
{
    return "修改物理 Jetty过程中依赖步骤失败";
}

std::string UrmaFailure081::GetRootCauseDesc() const
{
    return "函数用于修改物理 "
           "Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。";
}

RootCause UrmaFailure081::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure081::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure081::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_modify_jetty，modify pjetty fail, index:，, ret:。";
}

std::string UrmaFailure081::GetId() const
{
    return "urma_081";
}

} // namespace diag
