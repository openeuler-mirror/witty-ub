#include "urma_failure_178.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure178> g_urma("urma_178");

bool UrmaFailure178::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_alloc_jfr") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_alloc_jfr, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure178::GetName() const
{
    return "JFR临时结构分配失败导致分配JFR失败";
}

std::string UrmaFailure178::GetRootCauseDesc() const
{
    return "urma_cmd_alloc_jfr执行分配JFR前需要准备JFR临时结构，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure178::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure178::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure178::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_alloc_jfr，ioctl failed in urma_cmd_alloc_jfr, ret:，, "
           "errno:。";
}

std::string UrmaFailure178::GetId() const
{
    return "urma_178";
}
} // namespace diag
