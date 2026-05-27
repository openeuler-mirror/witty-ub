#include "urma_failure_385.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure385> g_urma("urma_385");

bool UrmaFailure385::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_trans_mode_valid' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'[DRV_ERR]Failed to create jfc, dev_name:' | grep -F ', eid_idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure385::GetName() const
{
    return "JFC创建时下层资源准备失败";
}

std::string UrmaFailure385::GetRootCauseDesc() const
{
    return "函数负责创建JFC，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure385::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure385::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure385::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_trans_mode_valid，[DRV_ERR]Failed to create jfc, "
           "dev_name:，, eid_idx:。";
}

std::string UrmaFailure385::GetId() const
{
    return "urma_385";
}

} // namespace diag
