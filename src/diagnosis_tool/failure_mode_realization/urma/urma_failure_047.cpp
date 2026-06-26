#include "urma_failure_047.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure047> g_urma("urma_047");

bool UrmaFailure047::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_init") != std::string::npos &&
           message.find("urma_init has been called before.") != std::string::npos;
}

std::string UrmaFailure047::GetName() const
{
    return "URMA资源状态不满足要求导致初始化URMA资源失败";
}

std::string UrmaFailure047::GetRootCauseDesc() const
{
    return "urma_init执行初始化URMA资源时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure047::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure047::GetFixSuggDesc() const
{
    return "查看/usr/lib64/urma目录下，是否存在liburma_udma.so等驱动文件，或查看文件是否具备x权限，完成正确部署后重试";
}

std::string UrmaFailure047::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_init，urma_init has been called before.。";
}

std::string UrmaFailure047::GetId() const
{
    return "urma_047";
}
} // namespace diag
