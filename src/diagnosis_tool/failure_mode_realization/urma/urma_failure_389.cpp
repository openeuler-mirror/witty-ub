#include "urma_failure_389.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure389> g_urma("urma_389");

bool UrmaFailure389::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_order_type' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F '[DRV_ERR]Failed to create jfs, dev_name:' | grep -F ', eid_idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure389::GetName() const
{
    return "JFS创建时下层资源准备失败";
}

std::string UrmaFailure389::GetRootCauseDesc() const
{
    return "函数负责创建JFS，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure389::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure389::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure389::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_check_order_type，[DRV_ERR]Failed to create jfs, dev_name:，, eid_idx:";
}

std::string UrmaFailure389::GetId() const
{
    return "urma_389";
}

} // namespace diag
