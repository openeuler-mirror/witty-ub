#include "urma_failure_504.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure504> g_urma("urma_504");

bool UrmaFailure504::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'import_check_tseg_by_import_result' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to import health check seg ('");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure504::GetName() const
{
    return "健康检查导入时下层资源准备失败";
}

std::string UrmaFailure504::GetRootCauseDesc() const
{
    return "函数负责导入健康检查，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure504::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure504::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure504::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：import_check_tseg_by_import_result，Failed to import health check seg (";
}

std::string UrmaFailure504::GetId() const
{
    return "urma_504";
}

} // namespace diag
