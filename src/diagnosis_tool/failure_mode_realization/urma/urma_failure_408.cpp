#include "urma_failure_408.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure408> g_urma("urma_408");

bool UrmaFailure408::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_query_eid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F '[DRV_ERR]Failed to create urma context.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure408::GetName() const
{
    return "context创建时下层资源准备失败";
}

std::string UrmaFailure408::GetRootCauseDesc() const
{
    return "函数负责创建context，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure408::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure408::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure408::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_query_eid，[DRV_ERR]Failed to create urma context.";
}

std::string UrmaFailure408::GetId() const
{
    return "urma_408";
}

} // namespace diag
