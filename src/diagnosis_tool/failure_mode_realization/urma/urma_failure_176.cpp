#include "urma_failure_176.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure176> g_urma("urma_176");

bool UrmaFailure176::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_alloc_jfs") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_alloc_jfr, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure176::GetName() const
{
    return "JFS临时结构分配失败导致分配JFS失败";
}

std::string UrmaFailure176::GetRootCauseDesc() const
{
    return "urma_cmd_alloc_jfs执行分配JFS前需要准备JFS临时结构，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure176::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure176::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure176::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_alloc_jfs，ioctl failed in urma_cmd_alloc_jfr, ret:，, "
           "errno:。";
}

std::string UrmaFailure176::GetId() const
{
    return "urma_176";
}
} // namespace diag
