#include "urma_1233_urma_open_cdev_file_path_is_not_standardize.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1233UrmaOpenCdevFilePathIsNotStandardize> g_urma("urma_1233");

bool Urma1233UrmaOpenCdevFilePathIsNotStandardize::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"file_path:% is not standardize."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1233UrmaOpenCdevFilePathIsNotStandardize::GetName() const
{
    return "urma_open_cdev file_path:% is not standardize.";
}

std::string Urma1233UrmaOpenCdevFilePathIsNotStandardize::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `file_path == NULL`；该路径返回 -1";
}

RootCause Urma1233UrmaOpenCdevFilePathIsNotStandardize::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1233UrmaOpenCdevFilePathIsNotStandardize::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1233UrmaOpenCdevFilePathIsNotStandardize::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：file_path:% is not standardize.";
}

std::string Urma1233UrmaOpenCdevFilePathIsNotStandardize::GetId() const
{
    return "urma_1233";
}
} // namespace diag
