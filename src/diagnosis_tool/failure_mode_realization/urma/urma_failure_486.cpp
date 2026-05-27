#include "urma_failure_486.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure486> g_urma("urma_486");

bool UrmaFailure486::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_parse_port_attr' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'snprintf failed, path:' | grep -F ', port_num:' | grep -F 'hu.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure486::GetName() const
{
    return "解析端口过程中依赖步骤失败";
}

std::string UrmaFailure486::GetRootCauseDesc() const
{
    return "函数用于解析端口，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure486::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure486::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure486::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_parse_port_attr，snprintf failed, path:，, port_num:，hu.。";
}

std::string UrmaFailure486::GetId() const
{
    return "urma_486";
}

} // namespace diag
