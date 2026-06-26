#include "urma_failure_048.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure048> g_urma("urma_048");

bool UrmaFailure048::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_init") != std::string::npos &&
           message.find("None of the providers registered.") != std::string::npos;
}

std::string UrmaFailure048::GetName() const
{
    return "URMA资源状态不满足要求导致初始化URMA资源失败";
}

std::string UrmaFailure048::GetRootCauseDesc() const
{
    return "urma_init执行初始化URMA资源时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure048::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure048::GetFixSuggDesc() const
{
    return "查看/usr/lib64/urma目录下，是否存在liburma_udma.so等驱动文件，或查看文件是否具备x权限，完成正确部署后重试";
}

std::string UrmaFailure048::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_init，None of the providers registered.。";
}

std::string UrmaFailure048::GetId() const
{
    return "urma_048";
}
} // namespace diag
