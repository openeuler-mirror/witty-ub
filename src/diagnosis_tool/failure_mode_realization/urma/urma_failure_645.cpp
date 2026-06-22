#include "urma_failure_645.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure645> g_urma("urma_645");

bool UrmaFailure645::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_read_sysfs_file") != std::string::npos &&
           message.find("snprintf failed") != std::string::npos;
}

std::string UrmaFailure645::GetName() const
{
    return "读取sysfs信息、FILE执行失败导致读取sysfs信息、FILE失败";
}

std::string UrmaFailure645::GetRootCauseDesc() const
{
    return "urma_read_sysfs_"
           "file执行读取sysfs信息、FILE时依赖的读取sysfs信息、FILE步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure645::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure645::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure645::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_read_sysfs_file，snprintf failed。";
}

std::string UrmaFailure645::GetId() const
{
    return "urma_645";
}
} // namespace diag
