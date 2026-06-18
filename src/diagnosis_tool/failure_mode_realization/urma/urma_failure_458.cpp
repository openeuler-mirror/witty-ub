#include "urma_failure_458.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure458> g_urma("urma_458");

bool UrmaFailure458::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_alloc_jfc") != std::string::npos &&
           message.find("failed to exec ops->alloc_jfc") != std::string::npos;
}

std::string UrmaFailure458::GetName() const
{
    return "JFC临时结构分配失败导致分配JFC失败";
}

std::string UrmaFailure458::GetRootCauseDesc() const
{
    return "urma_alloc_jfc执行分配JFC前需要准备JFC临时结构，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure458::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure458::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure458::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_jfc，failed to exec ops->alloc_jfc。";
}

std::string UrmaFailure458::GetId() const
{
    return "urma_458";
}
} // namespace diag
