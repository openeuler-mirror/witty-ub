#include "urma_failure_421.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure421> g_urma("urma_421");

bool UrmaFailure421::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_alloc_jfc") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_alloc_jfc, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure421::GetName() const
{
    return "JFC临时结构分配失败导致分配JFC失败";
}

std::string UrmaFailure421::GetRootCauseDesc() const
{
    return "urma_cmd_alloc_jfc执行分配JFC前需要准备JFC临时结构，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure421::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure421::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure421::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_alloc_jfc，ioctl failed in urma_cmd_alloc_jfc, ret:，, "
           "errno:。";
}

std::string UrmaFailure421::GetId() const
{
    return "urma_421";
}
} // namespace diag
