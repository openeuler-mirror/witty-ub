#include "urma_failure_557.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure557> g_urma("urma_557");

bool UrmaFailure557::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_get_device_by_name' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'urma get device list failed, device_num'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure557::GetName() const
{
    return "urma_get_device_by_name 执行获取 设备 失败导致当前资源状态无法推进";
}

std::string UrmaFailure557::GetRootCauseDesc() const
{
    return "urma_get_device_by_name 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure557::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure557::GetFixSuggDesc() const
{
    return "执行 `lsmod | grep udma` 检查驱动是否加载，执行 `urma_admin show -a` 查看 UB 设备是否存在，部署完成后重试";
}

std::string UrmaFailure557::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：urma get device list failed, device_num";
}

std::string UrmaFailure557::GetId() const
{
    return "urma_557";
}

} // namespace diag
