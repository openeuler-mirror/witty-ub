#include "urma_failure_390.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure390> g_urma("urma_390");

bool UrmaFailure390::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_alloc_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'jfc cfg depth of range, depth:' | grep -F ', max_depth:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure390::GetName() const
{
    return "分配JFC过程中依赖步骤失败";
}

std::string UrmaFailure390::GetRootCauseDesc() const
{
    return "函数用于分配JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure390::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure390::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure390::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_jfc，jfc cfg depth of range, depth:，, max_depth:。";
}

std::string UrmaFailure390::GetId() const
{
    return "urma_390";
}

} // namespace diag
