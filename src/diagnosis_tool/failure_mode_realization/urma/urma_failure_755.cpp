#include "urma_failure_755.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure755> g_urma("urma_755");

bool UrmaFailure755::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_open_cdev") != std::string::npos && message.find("file_path:") != std::string::npos &&
           message.find("is not standardize.") != std::string::npos;
}

std::string UrmaFailure755::GetName() const
{
    return "CDEV状态不满足要求导致打开CDEV失败";
}

std::string UrmaFailure755::GetRootCauseDesc() const
{
    return "urma_open_cdev执行打开CDEV时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure755::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure755::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure755::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_open_cdev，file_path:，is not standardize.。";
}

std::string UrmaFailure755::GetId() const
{
    return "urma_755";
}
} // namespace diag
