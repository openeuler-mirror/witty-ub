#include "urma_failure_382.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure382> g_urma("urma_382");

bool UrmaFailure382::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_trans_mode_valid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F '[DRV_ERR]Failed to create jfc, dev_name:' | grep -F ', eid_idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure382::GetName() const
{
    return "JFC创建时下层资源准备失败";
}

std::string UrmaFailure382::GetRootCauseDesc() const
{
    return "函数负责创建JFC，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure382::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure382::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure382::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_check_trans_mode_valid，[DRV_ERR]Failed to create jfc, dev_name:，, "
           "eid_idx:";
}

std::string UrmaFailure382::GetId() const
{
    return "urma_382";
}

} // namespace diag
